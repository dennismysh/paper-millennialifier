/**
 * Netlify Function: Translate a single paper section via LLM with SSE streaming.
 *
 * Accepts JSON body:
 *   { heading, content, tone (1-5), provider, model? }
 *
 * Returns: text/event-stream with events:
 *   chunk  — { text }    partial translation text
 *   done   — {}          translation finished
 *   error  — { message } something went wrong
 */

import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
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

async function* streamClaude(systemPrompt, userPrompt, model) {
  const client = new Anthropic();
  const stream = client.messages.stream({
    model: model || "claude-sonnet-4-20250514",
    max_tokens: 4096,
    system: systemPrompt,
    messages: [{ role: "user", content: userPrompt }],
  });

  for await (const event of stream) {
    if (
      event.type === "content_block_delta" &&
      event.delta?.type === "text_delta"
    ) {
      yield event.delta.text;
    }
  }
}

async function* streamOpenAICompat(
  systemPrompt,
  userPrompt,
  model,
  baseURL,
  apiKey
) {
  const client = new OpenAI({
    baseURL: baseURL || undefined,
    apiKey: apiKey || "not-needed",
  });

  const stream = await client.chat.completions.create({
    model,
    max_tokens: 4096,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    stream: true,
  });

  for await (const chunk of stream) {
    const text = chunk.choices[0]?.delta?.content;
    if (text) yield text;
  }
}

async function* streamGemini(systemPrompt, userPrompt, model) {
  // Netlify AI Gateway auto-injects GEMINI_API_KEY; fall back to manual key
  const ai = new GoogleGenAI({
    apiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY,
  });

  const response = await ai.models.generateContentStream({
    model: model || "gemini-2.0-flash",
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

// Provider registry
const PROVIDERS = {
  claude: {
    getStream: (sys, usr, model) => streamClaude(sys, usr, model),
    keyEnv: "ANTHROPIC_API_KEY",
  },
  openai: {
    getStream: (sys, usr, model) =>
      streamOpenAICompat(
        sys,
        usr,
        model || "gpt-4o",
        undefined,
        process.env.OPENAI_API_KEY
      ),
    keyEnv: "OPENAI_API_KEY",
  },
  gemini: {
    getStream: (sys, usr, model) => streamGemini(sys, usr, model),
    keyEnv: "GEMINI_API_KEY",
    altKeyEnv: "GOOGLE_API_KEY",
  },
  groq: {
    getStream: (sys, usr, model) =>
      streamOpenAICompat(
        sys,
        usr,
        model || "llama-3.3-70b-versatile",
        "https://api.groq.com/openai/v1",
        process.env.GROQ_API_KEY
      ),
    keyEnv: "GROQ_API_KEY",
  },
  openrouter: {
    getStream: (sys, usr, model) =>
      streamOpenAICompat(
        sys,
        usr,
        model || "meta-llama/llama-3.3-70b-instruct:free",
        "https://openrouter.ai/api/v1",
        process.env.OPENROUTER_API_KEY
      ),
    keyEnv: "OPENROUTER_API_KEY",
  },
};

// ---------------------------------------------------------------------------
// Friendly error messages
// ---------------------------------------------------------------------------

const KEY_ENV_NAMES = {
  claude: "ANTHROPIC_API_KEY",
  openai: "OPENAI_API_KEY",
  gemini: "GEMINI_API_KEY or GOOGLE_API_KEY",
  groq: "GROQ_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
};

function friendlyError(provider, err) {
  const raw = (err.message || "").toLowerCase();
  const envHint = KEY_ENV_NAMES[provider] ? ` (${KEY_ENV_NAMES[provider]})` : "";

  if (
    raw.includes("api key not valid") ||
    raw.includes("invalid api key") ||
    raw.includes("unauthorized") ||
    raw.includes("401")
  ) {
    return (
      `Your ${provider} API key${envHint} is invalid. ` +
      "Please double-check the key in your Netlify site environment variables."
    );
  }
  if (raw.includes("quota") || raw.includes("rate limit") || raw.includes("429")) {
    return (
      `Rate limit or quota exceeded for ${provider}. ` +
      "Please wait a moment and try again, or switch to another provider."
    );
  }
  if (raw.includes("not found") || raw.includes("404")) {
    return (
      `The requested model was not found on ${provider}. ` +
      "Please check the model name or leave it blank for the default."
    );
  }
  return `Error from ${provider}: ${err.message}`;
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

  const { heading, content, tone, provider: requestedProvider, model } = body;

  if (!content) {
    return Response.json(
      { error: "No content to translate." },
      { status: 400 }
    );
  }

  // Auto-select the first available provider if none is specified
  const provider = requestedProvider || Object.keys(PROVIDERS).find(name => {
    const cfg = PROVIDERS[name];
    return process.env[cfg.keyEnv] || (cfg.altKeyEnv && process.env[cfg.altKeyEnv]);
  }) || Object.keys(PROVIDERS)[0];

  const providerConfig = PROVIDERS[provider];
  if (!providerConfig) {
    return Response.json(
      { error: `Unknown provider: ${provider}. Available: ${Object.keys(PROVIDERS).join(", ")}` },
      { status: 400 }
    );
  }

  const hasKey = process.env[providerConfig.keyEnv] ||
    (providerConfig.altKeyEnv && process.env[providerConfig.altKeyEnv]);
  if (providerConfig.keyEnv && !hasKey) {
    return Response.json(
      {
        error: `Missing API key: ${providerConfig.keyEnv}. Add it in your Netlify site settings under Environment Variables. Providers like Claude, OpenAI, and Gemini may be available via Netlify AI Gateway without manual configuration.`,
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
      const stream = providerConfig.getStream(systemPrompt, userPrompt, model);
      for await (const chunk of stream) {
        await writeSSE("chunk", { text: chunk });
      }
      await writeSSE("done", {});
    } catch (err) {
      console.error("Translation error:", err);
      await writeSSE("error", { message: friendlyError(provider, err) });
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
