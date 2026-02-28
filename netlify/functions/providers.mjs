/**
 * Netlify Function: Return available LLM providers and their metadata.
 *
 * This app exclusively uses Google Gemini (gemini-2.0-flash) for translation.
 */

const PROVIDERS = [
  {
    name: "gemini",
    description: "Google Gemini \u2014 available via Netlify AI Gateway",
    default_model: "gemini-2.0-flash",
    free: true,
    keyEnv: "GEMINI_API_KEY",
    altKeyEnv: "GOOGLE_API_KEY",
  },
];

export default async (request) => {
  const providers = PROVIDERS.map(({ keyEnv, altKeyEnv, ...provider }) => ({
    ...provider,
    available: !!process.env[keyEnv] || (altKeyEnv && !!process.env[altKeyEnv]),
    keyEnv,
  }));
  return Response.json(providers);
};

export const config = {
  path: "/api/providers",
};
