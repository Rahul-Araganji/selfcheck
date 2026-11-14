// Original pixel art, drawn as SVG rectangles. Each sprite is rows of palette keys; "." is empty.
const PALETTE = {
  k: "#2b1d0e", // outline
  b: "#8b5a2b", // brown
  d: "#5c3a1a", // dark brown
  t: "#c9a26b", // tan
  w: "#f4ecd8", // paper
  g: "#5da130", // grass
  G: "#3e7a1e", // dark grass
  s: "#87ceeb", // sky
  S: "#3b8fc4", // deep sky
  y: "#f2c230", // gold
  Y: "#c8961a", // dark gold
  r: "#d64545", // red
  o: "#e98a2c", // orange
  e: "#ffffff", // eye white
  n: "#9a9a9a", // stone
  N: "#6b6b6b", // dark stone
  p: "#8e5bd6", // purple
};

const SPRITES = {
  owl: [
    "..k......k..",
    ".kbk....kbk.",
    ".kbbkkkkbbk.",
    "kbbbbbbbbbbk",
    "kbeekbbkeebk",
    "kbekkbbkkebk",
    "kbeekyykeebk",
    "kbbbkyykbbbk",
    "kbtttbbtttbk",
    "kbttbttbttbk",
    ".kbtttttttk.",
    ".kbbttttbbk.",
    "..kkokkokk..",
  ],
  book: [
    ".kkkkk.kkkkk.",
    "kGgggkkkgggGk",
    "kGwwwwkwwwwGk",
    "kGwkkwkwkkwGk",
    "kGwwwwkwwwwGk",
    "kGwkkwkwkkwGk",
    "kGwwwwkwwwwGk",
    "kGgggggggggGk",
    ".kkkkkkkkkkk.",
  ],
  sword: [
    ".......kk",
    "......kek",
    ".....kek.",
    "....kek..",
    ".k.kek...",
    "..kbk....",
    ".kbk.....",
    "kbk......",
  ],
  gem: [
    "..kkkk..",
    ".kssSSk.",
    "kseessSk",
    "kseSSSSk",
    ".kSSSSk.",
    "..kSSk..",
    "...kk...",
  ],
  chip: [
    ".k.k.k.k.",
    "kkkkkkkkk",
    ".knnnnnk.",
    "kknGGGnkk",
    ".knGgGnk.",
    "kknGGGnkk",
    ".knnnnnk.",
    "kkkkkkkkk",
    ".k.k.k.k.",
  ],
  clock: [
    ".kkkk.",
    "kyyyyk",
    "kyykyk",
    "kykkyk",
    "kyyyyk",
    ".kkkk.",
  ],
  hourglass: [
    "kkkkkk",
    ".kyyk.",
    "..ky..",
    "..yk..",
    ".kyyk.",
    "kkkkkk",
  ],
  trophy: [
    "kkkkkkkkk",
    "kyyyyyyyk",
    "kyeyyyyYk",
    "kyyyyyyYk",
    ".kyyyyYk.",
    "..kyyYk..",
    "...kYk...",
    "...kYk...",
    "..kbbbk..",
    ".kbbbbbk.",
    ".kkkkkkk.",
  ],
  heart: [
    ".kk.kk.",
    "krrkrrk",
    "krrrrrk",
    ".krrrk.",
    "..krk..",
    "...k...",
  ],
  heartBroken: [
    ".kk.kk.",
    "kNNkNNk",
    "kNkNNNk",
    ".kNkNk.",
    "..kNk..",
    "...k...",
  ],
  heartEmpty: [
    ".kk.kk.",
    "knnknnk",
    "knnnnnk",
    ".knnnk.",
    "..knk..",
    "...k...",
  ],
};

function spriteSVG(name, px) {
  const rows = SPRITES[name];
  if (!rows) return "";
  const w = Math.max(...rows.map((r) => r.length));
  let rects = "";
  rows.forEach((row, y) => {
    [...row].forEach((c, x) => {
      if (c !== "." && PALETTE[c]) rects += `<rect x="${x}" y="${y}" width="1.02" height="1.02" fill="${PALETTE[c]}"/>`;
    });
  });
  return `<svg viewBox="0 0 ${w} ${rows.length}" width="${w * px}" height="${rows.length * px}" ` +
    `shape-rendering="crispEdges" aria-hidden="true">${rects}</svg>`;
}

function paintArt(root = document) {
  root.querySelectorAll(".art[data-art]").forEach((el) => {
    el.innerHTML = spriteSVG(el.dataset.art, Number(el.dataset.px || 4));
  });
}
