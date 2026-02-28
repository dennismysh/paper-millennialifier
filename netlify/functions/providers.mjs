/**
 * Netlify Function: Return available LLM providers and their metadata.
 *
 * Checks which API keys are configured (either via Netlify AI inference
 * or manually set env vars) and marks providers as available/unavailable
 * so the frontend can guide users accordingly.
 */

const PROVIDERS = [
  {
    name: "claude",
    description: "Anthropic Claude",
    default_model: "claude-sonnet-4-20250514",
    free: false,
    keyEnv: "ANTHROPIC_API_KEY",
  },
  {
    name: "openai",
    description: "OpenAI (GPT-4o, etc.)",
    default_model: "gpt-4o",
    free: false,
    keyEnv: "OPENAI_API_KEY",
  },
  {
    name: "gemini",
    description: "Google Gemini \u2014 generous free tier",
    default_model: "gemini-2.0-flash",
    free: true,
    keyEnv: "GOOGLE_API_KEY",
  },
  {
    name: "groq",
    description: "Groq \u2014 fast inference, free tier (Llama 3.3, Mixtral)",
    default_model: "llama-3.3-70b-versatile",
    free: true,
    keyEnv: "GROQ_API_KEY",
  },
  {
    name: "openrouter",
    description: "OpenRouter \u2014 model aggregator with free options",
    default_model: "meta-llama/llama-3.3-70b-instruct:free",
    free: true,
    keyEnv: "OPENROUTER_API_KEY",
  },
];

export default async (request) => {
  const providers = PROVIDERS.map(({ keyEnv, ...provider }) => ({
    ...provider,
    available: !!process.env[keyEnv],
    keyEnv,
  }));
  return Response.json(providers);
};

export const config = {
  path: "/api/providers",
};
