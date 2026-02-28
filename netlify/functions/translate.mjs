/**
 * Netlify Function: Translate a single paper section via Gemini with SSE streaming.
 *
 * Uses gemini-2.0-flash exclusively for all translations.
 *
 * Accepts JSON body:
 *   { heading, content, tone (1-5) }
 *
 * Returns: text/event-stream with events:
 *   chunk  — { text }    partial translation text
 *   done   — {}          translation finished
 *   error  — { message } something went wrong
 */

import { GoogleGenAI } from "@google/genai";

// ---------------------------------------------------------------------------
// Prompts (ported from src/millennialifier/prompts.py)
// ---------------------------------------------------------------------------

const BASE_INSTRUCTIONS = `\
You are translating a section of a PhD-level research paper into millennial speak.

Rules:
- Preserve ALL factual content, findings, and scientific meaning.
- Keep technical terms but explain them in parenthetical asides when helpful.
- Maintain the section structure (paragraphs, key points).
- Do NOT add information that isn't in the original.
- Do NOT remove important caveats, limitations, or nuance.
- If there are equations or formulas, keep them but add a casual explanation.
- Output ONLY the translated text. No meta-commentary about the translation.
`;

const TONE_INSTRUCTIONS = {
  1: `\
Tone: Light casual. Think "explaining your research at a dinner party."
- Use conversational language but keep it relatively professional.
- Occasional informal phrasing ("turns out," "basically," "pretty wild").
- Minimal slang. No emojis.
- Like a well-written blog post by a grad student.
`,
  2: `\
Tone: Moderately casual. Think "texting a smart friend about your thesis."
- Clearly informal but still coherent and structured.
- Use some millennial slang ("lowkey," "honestly," "it's giving").
- Light humor and relatable analogies welcome.
- Occasional rhetorical asides ("yes, really").
`,
  3: `\
Tone: Balanced millennial. Think "a podcast host who has a PhD but also goes to brunch."
- Confident casual voice with solid millennial energy.
- Use slang naturally ("literally," "I'm not gonna lie," "let's unpack this," "big yikes").
- Pop culture analogies where they actually clarify things.
- Self-aware humor about how dense the original material is.
- Still clearly communicates the science \u2014 the vibe is accessible, not dumbed down.
`,
  4: `\
Tone: Heavy millennial. Think "your most dramatic friend who also happens to be brilliant."
- Very casual, high slang density ("no cap," "rent-free," "main character energy," "the vibes are immaculate").
- Dramatic reactions to findings ("I am DECEASED," "this is sending me").
- Frequent pop culture references and analogies.
- Emoji use is acceptable but not required.
- The science is still there, just wrapped in peak millennial delivery.
`,
  5: `\
Tone: Full unhinged millennial chaos. Think "chaotic group chat energy from someone defending their dissertation."
- Maximum slang, maximum drama, maximum relatability.
- Stream-of-consciousness asides, ALL CAPS moments, emoji flourishes.
- "bestie let me tell you" energy throughout.
- Every finding gets a dramatic reaction.
- References to avocado toast, therapy, existential dread, and vibes are encouraged.
- THE SCIENCE MUST STILL BE CORRECT. This is unhinged in delivery, not in accuracy.
`,
};

function buildSystemPrompt(tone) {
  return BASE_INSTRUCTIONS + "\n" + (TONE_INSTRUCTIONS[tone] || TONE_INSTRUCTIONS[3]);
}

function buildSectionPrompt(heading, content) {
  return (
    `Translate this paper section into millennial speak.\n\n` +
    `## Section: ${heading}\n\n` +
    content
  );
}

// ---------------------------------------------------------------------------
// LLM provider streaming
// ---------------------------------------------------------------------------

async function* streamGemini(systemPrompt, userPrompt) {
  // Netlify AI Gateway auto-injects GEMINI_API_KEY; fall back to manual key
  const ai = new GoogleGenAI({
    apiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY,
  });

  const response = await ai.models.generateContentStream({
    model: "gemini-2.0-flash",
    contents: userPrompt,
    config: {
      systemInstruction: systemPrompt,
      maxOutputTokens: 4096,
    },
  });

  for await (const chunk of response) {
    const text = chunk.text;
    if (text) yield text;
  }
}

// ---------------------------------------------------------------------------
// Friendly error messages
// ---------------------------------------------------------------------------

function friendlyError(err) {
  const raw = (err.message || "").toLowerCase();

  if (
    raw.includes("api key not valid") ||
    raw.includes("invalid api key") ||
    raw.includes("unauthorized") ||
    raw.includes("401")
  ) {
    return (
      "Your Gemini API key (GEMINI_API_KEY or GOOGLE_API_KEY) is invalid. " +
      "Please double-check the key in your Netlify site environment variables."
    );
  }
  if (raw.includes("quota") || raw.includes("rate limit") || raw.includes("429")) {
    return (
      "Rate limit or quota exceeded for Gemini. " +
      "Please wait a moment and try again."
    );
  }
  if (raw.includes("not found") || raw.includes("404")) {
    return (
      "The Gemini model was not found. " +
      "Please check your Gemini API configuration."
    );
  }
  return `Error from Gemini: ${err.message}`;
}

// ---------------------------------------------------------------------------
// Netlify Function handler
// ---------------------------------------------------------------------------

export default async (request) => {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }

  if (request.method !== "POST") {
    return Response.json({ error: "Method not allowed" }, { status: 405 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { heading, content, tone } = body;

  if (!content) {
    return Response.json(
      { error: "No content to translate." },
      { status: 400 }
    );
  }

  const hasKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!hasKey) {
    return Response.json(
      {
        error: "Missing API key: GEMINI_API_KEY or GOOGLE_API_KEY. Add it in your Netlify site settings under Environment Variables.",
      },
      { status: 400 }
    );
  }

  const systemPrompt = buildSystemPrompt(tone || 3);
  const userPrompt = buildSectionPrompt(heading || "Section", content);

  // Stream the translation as SSE
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const encoder = new TextEncoder();

  const writeSSE = async (event, data) => {
    await writer.write(
      encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
    );
  };

  // Run the LLM streaming in the background
  (async () => {
    try {
      const stream = streamGemini(systemPrompt, userPrompt);
      for await (const chunk of stream) {
        await writeSSE("chunk", { text: chunk });
      }
      await writeSSE("done", {});
    } catch (err) {
      console.error("Translation error:", err);
      await writeSSE("error", { message: friendlyError(err) });
    } finally {
      await writer.close();
    }
  })();

  return new Response(readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
};

export const config = {
  path: "/api/translate",
};
