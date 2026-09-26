"use strict";
(() => {
  const search = document.getElementById("skill-search");
  if (!search) return;
  const category = document.getElementById("category");
  const cards = [...document.querySelectorAll(".skill-card")];
  const count = document.getElementById("result-count");
  const empty = document.getElementById("no-results");
  function filter() {
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const card of cards) {
      const match = (!category.value || category.value === card.dataset.category) && terms.every(term => card.dataset.search.includes(term));
      card.hidden = !match;
      shown += Number(match);
    }
    count.textContent = `${shown} / ${cards.length} 个技能`;
    empty.hidden = shown !== 0;
  }
  search.addEventListener("input", filter);
  category.addEventListener("change", filter);
})();
