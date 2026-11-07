import { existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
const here = new URL('.', import.meta.url);
export async function resolve(spec, ctx, next) {
  if (spec === '@babel/parser') return { url: new URL('babel-parser-shim.mjs', here).href, shortCircuit: true };
  if (spec === '@babel/types') return { url: new URL('babel-types-shim.mjs', here).href, shortCircuit: true };
  if ((spec.startsWith('.') || spec.startsWith('/')) && spec.endsWith('.js') && ctx.parentURL) {
    const u = new URL(spec, ctx.parentURL);
    if (!existsSync(fileURLToPath(u))) {
      const ts = new URL(spec.slice(0, -3) + '.ts', ctx.parentURL);
      if (existsSync(fileURLToPath(ts))) return { url: ts.href, shortCircuit: true };
    }
  }
  return next(spec, ctx);
}
