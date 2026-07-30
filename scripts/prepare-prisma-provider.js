#!/usr/bin/env node
/**
 * Switch Prisma datasource provider to match DATABASE_URL before migrate/generate.
 * sqlite: file:… or sqlite:…
 * otherwise: postgresql
 */
const fs = require("node:fs");
const path = require("node:path");

const schemaPath = path.join(__dirname, "..", "prisma", "schema.prisma");
const url = process.env.DATABASE_URL || "";
const provider =
  url.startsWith("file:") || url.startsWith("sqlite:") ? "sqlite" : "postgresql";

let schema = fs.readFileSync(schemaPath, "utf8");
schema = schema.replace(
  /provider\s*=\s*"(sqlite|postgresql)"/,
  `provider = "${provider}"`,
);
fs.writeFileSync(schemaPath, schema);
console.log(`Prisma provider set to ${provider}`);
