/**
 * Netlify Function: Return available LLM providers and their metadata.
 */

const PROVIDERS = [
  {
    name: "claude",
    description: "Anthropic Claude",
    default_model: "claude-sonnet-4-20250514",
    free: false,
  },
  {
    name: "openai",
    description: "OpenAI (GPT-4o, etc.)",
    default_model: "gpt-4o",
    free: false,
  },
  {
    name: "gemini",
    description: "Google Gemini \u2014 generous free tier",
    default_model: "gemini-2.0-flash",
    free: true,
  },
  {
    name: "groq",
    description: "Groq \u2014 fast inference, free tier (Llama 3.3, Mixtral)",
    default_model: "llama-3.3-70b-versatile",
    free: true,
  },
  {
    name: "openrouter",
    description: "OpenRouter \u2014 model aggregator with free options",
    default_model: "meta-llama/llama-3.3-70b-instruct:free",
    free: true,
  },
];

export default async (request) => {
  return Response.json(PROVIDERS);
};

export const config = {
  path: "/api/providers",
};
