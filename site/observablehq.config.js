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
  footer: "Sources: Tanzania Police Force / NBS, WHO, news reports. Ajali TZ."
};
