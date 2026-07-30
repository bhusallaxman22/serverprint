import { PDFDocument } from "pdf-lib";
import path from "node:path";
import sharp from "sharp";

export const ALLOWED_EXTENSIONS = new Set([".pdf", ".png", ".jpg", ".jpeg"]);
export const ALLOWED_MIME = new Set(["application/pdf", "image/png", "image/jpeg"]);

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const JPEG_SOI = Buffer.from([0xff, 0xd8]);
const PDF_SIGNATURE = Buffer.from("%PDF-");

export class DocumentValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DocumentValidationError";
  }
}

export type DocumentMetadata = {
  extension: string;
  mimeType: string;
  pageCount: number;
};

function inferSignatureMime(content: Buffer): string | null {
  if (content.subarray(0, 5).equals(PDF_SIGNATURE)) return "application/pdf";
  if (content.subarray(0, 8).equals(PNG_SIGNATURE)) return "image/png";
  if (content.subarray(0, 2).equals(JPEG_SOI)) return "image/jpeg";
  return null;
}

async function countPdfPages(content: Buffer): Promise<number> {
  try {
    const doc = await PDFDocument.load(content, { ignoreEncryption: false });
    return doc.getPageCount();
  } catch {
    throw new DocumentValidationError("The PDF is unreadable, malformed, or encrypted.");
  }
}

async function countImageFrames(content: Buffer): Promise<number> {
  try {
    const meta = await sharp(content, { animated: true }).metadata();
    return meta.pages && meta.pages > 0 ? meta.pages : 1;
  } catch {
    throw new DocumentValidationError("The uploaded image is unreadable.");
  }
}

export async function validateDocument(
  filename: string,
  providedMime: string | null | undefined,
  content: Buffer,
): Promise<DocumentMetadata> {
  const extension = path.extname(filename).toLowerCase();
  if (!ALLOWED_EXTENSIONS.has(extension)) {
    throw new DocumentValidationError("Unsupported file type.");
  }

  const signatureMime = inferSignatureMime(content);
  if (!signatureMime) {
    throw new DocumentValidationError("The uploaded file is not a valid PDF or image.");
  }

  const normalizedProvided = (providedMime ?? "").split(";")[0].trim().toLowerCase();
  if (normalizedProvided && !ALLOWED_MIME.has(normalizedProvided)) {
    throw new DocumentValidationError("Unsupported file type.");
  }
  if (normalizedProvided && normalizedProvided !== signatureMime) {
    throw new DocumentValidationError("File content does not match declared file type.");
  }

  const pageCount =
    signatureMime === "application/pdf"
      ? await countPdfPages(content)
      : await countImageFrames(content);

  return { extension, mimeType: signatureMime, pageCount };
}
