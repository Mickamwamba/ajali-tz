// Observable Framework configuration for the Ajali TZ dashboard.
// Pages live in src/; data loaders in src/data/ read the pipeline's outputs in ../data/.
export default {
  title: "Ajali TZ",
  pages: [
    {name: "Map", path: "/map"},
    {name: "Recent crashes", path: "/crashes"},
    {name: "About the data", path: "/about"}
  ],
  root: "src",
  output: "dist",
  theme: ["air", "near-midnight"], // light and dark, following the reader's system setting
  search: false,
  head: `<style>
    .share-button { margin-top: 0.5rem; padding: 0.35rem 0.8rem; border-radius: 6px; font: inherit; font-size: 0.85rem; cursor: pointer;
      border: 1px solid var(--theme-foreground-faint); background: var(--theme-background); color: var(--theme-foreground); }
    .share-button:hover { border-color: var(--theme-foreground-focus); }
    .share-button:focus-visible { outline: 2px solid var(--theme-foreground-focus); outline-offset: 2px; }
    .share-button:disabled { opacity: 0.7; cursor: progress; }
  </style>`,
  footer: "Sources: Tanzania Police Force / NBS, WHO, news reports. Ajali TZ."
};
