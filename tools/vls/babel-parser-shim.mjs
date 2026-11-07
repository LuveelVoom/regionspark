// Minimal stand-in for @babel/parser's parseExpression, producing the node shapes
// vls's runExpression reads: Identifier, NumericLiteral, BooleanLiteral, UnaryExpression,
// BinaryExpression, LogicalExpression, ConditionalExpression, CallExpression.
const BIN = [['||'], ['&&'], ['|'], ['^'], ['&'], ['==', '!='], ['<', '<=', '>', '>='], ['<<', '>>', '>>>'], ['+', '-'], ['*', '/', '%']];
export function parseExpression(src) {
  const toks = []; let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (/\s/.test(c)) { i++; continue; }
    let m;
    if ((m = /^(\d+\.?\d*|\.\d+)/.exec(src.slice(i)))) { toks.push({ k: 'num', v: Number(m[0]) }); i += m[0].length; continue; }
    if ((m = /^[A-Za-z_$][\w$]*/.exec(src.slice(i)))) { toks.push({ k: 'id', v: m[0] }); i += m[0].length; continue; }
    if ((m = /^(>>>|\*\*|<<|>>|<=|>=|==|!=|&&|\|\||[-+*\/%<>&|^(),?:!~])/.exec(src.slice(i)))) { toks.push({ k: 'op', v: m[0] }); i += m[0].length; continue; }
    throw new Error('unexpected character ' + c);
  }
  let p = 0;
  const peek = () => toks[p], take = () => toks[p++];
  const expect = v => { const t = take(); if (!t || t.v !== v) throw new Error('expected ' + v); };
  function cond() {
    const test = bin(0);
    if (peek() && peek().v === '?') { take(); const a = cond(); expect(':'); const b = cond(); return { type: 'ConditionalExpression', test, consequent: a, alternate: b }; }
    return test;
  }
  function bin(level) {
    if (level === BIN.length) return pow();
    let left = bin(level + 1);
    while (peek() && peek().k === 'op' && BIN[level].includes(peek().v)) {
      const op = take().v; const right = bin(level + 1);
      left = { type: op === '&&' || op === '||' ? 'LogicalExpression' : 'BinaryExpression', operator: op, left, right };
    }
    return left;
  }
  function pow() {
    const base = unary();
    if (peek() && peek().v === '**') { take(); return { type: 'BinaryExpression', operator: '**', left: base, right: pow() }; }
    return base;
  }
  function unary() {
    const t = peek();
    if (t && t.k === 'op' && ['-', '+', '!', '~'].includes(t.v)) { take(); return { type: 'UnaryExpression', operator: t.v, prefix: true, argument: unary() }; }
    return primary();
  }
  function primary() {
    const t = take();
    if (!t) throw new Error('unexpected end');
    if (t.k === 'num') return { type: 'NumericLiteral', value: t.v };
    if (t.k === 'id') {
      if (t.v === 'true' || t.v === 'false') return { type: 'BooleanLiteral', value: t.v === 'true' };
      const id = { type: 'Identifier', name: t.v };
      if (peek() && peek().v === '(') {
        take(); const args = [];
        if (peek().v !== ')') { args.push(cond()); while (peek().v === ',') { take(); args.push(cond()); } }
        expect(')'); return { type: 'CallExpression', callee: id, arguments: args };
      }
      return id;
    }
    if (t.v === '(') { const e = cond(); expect(')'); return e; }
    throw new Error('unexpected ' + t.v);
  }
  const e = cond();
  if (p !== toks.length) throw new Error('trailing input');
  return e;
}
