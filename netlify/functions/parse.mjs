/**
 * Netlify Function: Parse a research paper from URL or uploaded file.
 *
 * Accepts JSON body:
 *   { url: string }              — fetch and parse from URL
 *   { file: string (base64), filename: string } — parse an uploaded file
 *
 * Returns JSON: { title, authors, sections: [{ heading, content }] }
 */

import { load } from "cheerio";

// ---------------------------------------------------------------------------
// arXiv helpers
// ---------------------------------------------------------------------------

const ARXIV_ABS_RE = /arxiv\.org\/abs\/([\w.]+)/;
const ARXIV_PDF_RE = /arxiv\.org\/pdf\/([\w.]+)/;

function getArxivId(url) {
  for (const re of [ARXIV_ABS_RE, ARXIV_PDF_RE]) {
    const m = url.match(re);
    if (m) return m[1];
  }
  return null;
}

// ---------------------------------------------------------------------------
// HTML parsing (cheerio — Node equivalent of BeautifulSoup)
// ---------------------------------------------------------------------------

const SKIP_HEADINGS = new Set([
  "references",
  "bibliography",
  "acknowledgements",
  "acknowledgments",
]);

function parseHtml(html) {
  const $ = load(html);

  // Title
  let title = "Untitled";
  for (const cls of ["ltx_title", "document-title", "title"]) {
    const tag = $(`.${cls}`).first();
    if (tag.length) {
      title = tag.text().trim();
      break;
    }
  }
  if (title === "Untitled" && $("title").length) {
    title = $("title").text().trim();
  }

  // Authors
  const authors = [];
  $(".ltx_personname").each((_, el) => {
    const name = $(el).text().trim();
    if (name) authors.push(name);
  });
  if (!authors.length) {
    $('meta[name="author"]').each((_, el) => {
      const content = $(el).attr("content");
      if (content) authors.push(content);
    });
  }

  // Abstract
  let abstract = "";
  for (const cls of ["ltx_abstract", "abstract"]) {
    const tag = $(`.${cls}`).first();
    if (tag.length) {
      tag.find(".ltx_title").remove();
      abstract = tag.text().trim();
      break;
    }
  }

  // Sections
  const sections = [];
  const ltxSections = $(".ltx_section");

  if (ltxSections.length) {
    // arXiv HTML structure
    ltxSections.each((_, sec) => {
      const $sec = $(sec);
      const headingTag = $sec.find(".ltx_title").first();
      const heading = headingTag.length
        ? headingTag.text().trim()
        : "Untitled Section";

      if (SKIP_HEADINGS.has(heading.toLowerCase())) return;

      headingTag.remove();
      const content = $sec.text().trim();
      if (content) sections.push({ heading, content });
    });
  } else {
    // Generic: walk heading tags
    const HEADING_TAGS = new Set(["h1", "h2", "h3", "h4"]);
    let currentHeading = null;
    let currentParts = [];

    const body = $("body").length ? $("body") : $.root();
    body.children().each((_, el) => {
      const $el = $(el);
      const tag = el.tagName?.toLowerCase();

      if (HEADING_TAGS.has(tag)) {
        if (currentHeading !== null) {
          const content = currentParts.join("\n").trim();
          if (content && !SKIP_HEADINGS.has(currentHeading.toLowerCase())) {
            sections.push({ heading: currentHeading, content });
          }
        }
        currentHeading = $el.text().trim();
        currentParts = [];
      } else if (currentHeading !== null) {
        const text = $el.text().trim();
        if (text) currentParts.push(text);
      }
    });

    // Last section
    if (currentHeading !== null) {
      const content = currentParts.join("\n").trim();
      if (content && !SKIP_HEADINGS.has(currentHeading.toLowerCase())) {
        sections.push({ heading: currentHeading, content });
      }
    }

    // Fallback: all text as one section
    if (!sections.length) {
      const allText = $.root().text().trim();
      if (allText) sections.push({ heading: "Full Paper", content: allText });
    }
  }

  // Combine abstract + sections
  const allSections = [];
  if (abstract) allSections.push({ heading: "Abstract", content: abstract });
  allSections.push(...sections);

  return { title, authors, sections: allSections };
}

// ---------------------------------------------------------------------------
// PDF parsing
// ---------------------------------------------------------------------------

const HEADING_PATTERNS = [
  /^(?:\d+\.?\s+)?(abstract)$/i,
  /^(?:\d+\.?\s+)?(introduction)$/i,
  /^(?:\d+\.?\s+)?(related\s+work)$/i,
  /^(?:\d+\.?\s+)?(background)$/i,
  /^(?:\d+\.?\s+)?(method(?:ology|s)?)$/i,
  /^(?:\d+\.?\s+)?(approach)$/i,
  /^(?:\d+\.?\s+)?(experiment(?:s|al\s+(?:setup|results))?)$/i,
  /^(?:\d+\.?\s+)?(results?)$/i,
  /^(?:\d+\.?\s+)?(evaluation)$/i,
  /^(?:\d+\.?\s+)?(discussion)$/i,
  /^(?:\d+\.?\s+)?(conclusion(?:s)?)$/i,
  /^(?:\d+\.?\s+)?(future\s+work)$/i,
  /^(?:\d+\.?\s+)?(acknowledge?ments?)$/i,
  /^(?:\d+\.?\s+)?(references?)$/i,
  /^(?:\d+\.?\s+)?(appendi(?:x|ces))$/i,
  /^(\d+\.?\s+\S.{2,60})$/,
];

function isHeading(line) {
  const s = line.trim();
  if (!s || s.length > 80) return false;
  return HEADING_PATTERNS.some((re) => re.test(s));
}

function cleanHeading(line) {
  const s = line.trim();
  const cleaned = s.replace(/^\d+(?:\.\d+)*\.?\s*/, "");
  if (!cleaned) return s;
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

async function parsePdf(buffer) {
  const pdf = (await import("pdf-parse")).default;
  const data = await pdf(buffer);
  const text = data.text;

  const lines = text.split("\n");

  // Title = first non-empty line
  let title = "Untitled";
  for (const line of lines) {
    if (line.trim()) {
      title = line.trim();
      break;
    }
  }

  const sections = [];
  let abstract = "";
  let currentHeading = null;
  let currentLines = [];
  let inBody = false;

  for (const line of lines) {
    if (isHeading(line)) {
      if (currentHeading !== null) {
        const body = currentLines.join("\n").trim();
        if (currentHeading.toLowerCase() === "abstract") {
          abstract = body;
        } else {
          sections.push({ heading: currentHeading, content: body });
        }
      }
      currentHeading = cleanHeading(line);
      currentLines = [];
      inBody = true;
    } else if (inBody) {
      currentLines.push(line);
    }
  }

  // Last section
  if (currentHeading !== null) {
    const body = currentLines.join("\n").trim();
    if (currentHeading.toLowerCase() === "abstract") {
      abstract = body;
    } else {
      sections.push({ heading: currentHeading, content: body });
    }
  }

  if (!sections.length && !abstract) {
    sections.push({ heading: "Full Paper", content: text.trim() });
  }

  const allSections = [];
  if (abstract) allSections.push({ heading: "Abstract", content: abstract });
  allSections.push(...sections);

  return { title, authors: [], sections: allSections };
}

// ---------------------------------------------------------------------------
// Remote fetching (arXiv-aware)
// ---------------------------------------------------------------------------

async function fetchPaper(url) {
  const arxivId = getArxivId(url);

  if (arxivId) {
    // Try arXiv HTML first (cleaner parsing)
    const htmlUrl = `https://arxiv.org/html/${arxivId}`;
    try {
      const resp = await fetch(htmlUrl);
      if (
        resp.ok &&
        (resp.headers.get("content-type") || "").includes("text/html")
      ) {
        return parseHtml(await resp.text());
      }
    } catch {
      // Fall through to PDF
    }

    // Fall back to PDF
    const pdfUrl = `https://arxiv.org/pdf/${arxivId}`;
    const resp = await fetch(pdfUrl);
    if (!resp.ok) throw new Error(`Failed to fetch arXiv PDF (${resp.status})`);
    const buf = Buffer.from(await resp.arrayBuffer());
    return parsePdf(buf);
  }

  // Non-arXiv URL — guess format from content-type
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to fetch URL (${resp.status})`);
  const ct = resp.headers.get("content-type") || "";

  if (ct.includes("pdf")) {
    const buf = Buffer.from(await resp.arrayBuffer());
    return parsePdf(buf);
  }

  return parseHtml(await resp.text());
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

  try {
    const body = await request.json();
    let paper;

    if (body.url) {
      paper = await fetchPaper(body.url);
    } else if (body.file) {
      const buffer = Buffer.from(body.file, "base64");
      const ext = (body.filename || "").split(".").pop().toLowerCase();
      if (ext === "pdf") {
        paper = await parsePdf(buffer);
      } else {
        paper = parseHtml(buffer.toString("utf-8"));
      }
    } else {
      return Response.json(
        { error: "Please provide a URL or upload a file." },
        { status: 400 }
      );
    }

    return Response.json(paper);
  } catch (err) {
    console.error("Parse error:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
};

export const config = {
  path: "/api/parse",
};
