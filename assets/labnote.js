// SPDX-License-Identifier: AGPL-3.0-only

for (const anchor of document.querySelectorAll(".heading-anchor")) {
  anchor.addEventListener("click", async () => {
    const url = new URL(anchor.getAttribute("href"), location.href);
    history.replaceState(null, "", url.hash);
    document.querySelector(url.hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      await navigator.clipboard.writeText(url.href);
      anchor.dataset.copied = "true";
      anchor.title = "Copied";
      window.setTimeout(() => { delete anchor.dataset.copied; anchor.title = "Copy link to this section"; }, 1400);
    } catch {
      anchor.title = "Section selected; copy the URL from the address bar";
    }
  });
}
