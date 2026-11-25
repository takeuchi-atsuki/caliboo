import { readFileSync, readdirSync } from "node:fs";
import { dirname, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";
import ts from "typescript";

// !NOTE: 正式ビルドの通常画面(index.html)を対象にする。
// 別エントリのモデル閲覧ページや、未訪問の画面のJSは合計に含めない。
const dist = resolve(process.argv[2] ?? resolve(dirname(fileURLToPath(import.meta.url)), "../dist"));
const index = readFileSync(resolve(dist, "index.html"), "utf8");

function localFile(parent, specifier) {
  const file = specifier.startsWith("/")
    ? resolve(dist, "." + specifier)
    : resolve(parent, specifier);
  if (!file.startsWith(dist + sep)) throw new Error("JS参照がdistの外を指しています: " + specifier);
  return file;
}

function entryFiles() {
  const refs = [];
  for (const match of index.matchAll(/<(script|link)\b[^>]*>/gi)) {
    const attrs = Object.fromEntries(
      [...match[0].matchAll(/([\w-]+)\s*=\s*["']([^"']+)["']/g)].map(
        ([, name, value]) => [name.toLowerCase(), value],
      ),
    );
    const ref = match[1] === "script" && attrs.type === "module"
      ? attrs.src
      : match[1] === "link" && attrs.rel === "modulepreload" ? attrs.href : undefined;
    if (ref?.endsWith(".js") && !/^(?:[a-z]+:|\/\/)/i.test(ref)) {
      refs.push(localFile(dist, ref));
    }
  }
  if (!refs.length) throw new Error("index.htmlにJSエントリが見つかりません。npm run buildを実行してください。");
  return refs;
}

const root = entryFiles();
const assets = resolve(dist, "assets");
const assetNames = readdirSync(assets);

function pageChunk(name) {
  const matches = assetNames.filter((file) => file.startsWith(name + "-") && file.endsWith(".js"));
  if (matches.length > 1) throw new Error("JSチャンクを1件に特定できません: " + name);
  // 分割前のビルドでは個別チャンクが存在せず、初期エントリに含まれている。
  return matches.map((file) => resolve(assets, file));
}

function measure(files) {
  const sizes = new Map();
  function visit(file) {
    if (sizes.has(file)) return;
    const source = readFileSync(file);
    sizes.set(file, gzipSync(source).length);
    const ast = ts.createSourceFile(file, source.toString(), ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
    for (const statement of ast.statements) {
      // 静的依存 (import / re-export) の推移閉包を走査する。動的importは訪問画面だけを追加する。
      if (!(ts.isImportDeclaration(statement) || ts.isExportDeclaration(statement))) continue;
      const specifier = statement.moduleSpecifier;
      if (specifier && ts.isStringLiteral(specifier) && /^[./]/.test(specifier.text)) {
        visit(localFile(dirname(file), specifier.text));
      }
    }
  }
  files.forEach(visit);
  return {
    gzipBytes: [...sizes.values()].reduce((total, size) => total + size, 0),
    files: [...sizes.entries()].map(([file, gzipBytes]) => ({ file: relative(dist, file), gzipBytes })),
  };
}

const login = pageChunk("LoginPage");
const home = pageChunk("HomePage");
console.log(JSON.stringify({
  initial: measure(root),
  coldLogin: measure([...root, ...login]),
  coldAuthenticatedHome: measure([...root, ...home]),
  loginThenHome: measure([...root, ...login, ...home]),
}, null, 2));
