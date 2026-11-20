"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const all = (selector, root = document) => [...root.querySelectorAll(selector)];
const code = document.body.dataset.company;
const picker = $("#company-picker");
if (picker) {
    picker.addEventListener("change", () => {
        if (picker.value) location.assign(picker.value);
    });
}
document.addEventListener("click", event => {
    const switcher = event.target.closest("[data-mode]");
    if (switcher) {
        const figure = switcher.closest("figure");
        all("[data-mode]", figure).forEach(btn => btn.setAttribute("aria-pressed", String(btn === switcher)));
        all("[data-view]", figure).forEach(view => { view.hidden = view.dataset.view !== switcher.dataset.mode; });
    }
    if (event.target.closest(".rail a") && matchMedia("(max-width: 600px)").matches) $(".rail details").open = false;
});
const updateProgress = () => {
    const bar = $(".progress");
    if (!bar) return;
    const length = document.documentElement.scrollHeight - innerHeight;
    bar.style.width = Math.max(0, Math.min(100, length > 0 ? 100 * scrollY / length : 0)) + "%";
};
if (code) {
    const narrow = matchMedia("(max-width: 600px)");
    const syncDirectory = () => { $(".rail details").open = !narrow.matches; };
    syncDirectory();
    narrow.addEventListener("change", syncDirectory);
    addEventListener("scroll", updateProgress, { passive: true });
    addEventListener("resize", updateProgress);
    updateProgress();
    const observer = new IntersectionObserver(entries => {
        const selected = entries.find(entry => entry.isIntersecting);
        if (!selected) return;
        all(".rail nav a").forEach(a => {
            if (a.hash === "#" + selected.target.id) a.setAttribute("aria-current", "true");
            else a.removeAttribute("aria-current");
        });
    }, { rootMargin: "-18% 0px -65% 0px" });
    all(".chapter").forEach(chapter => observer.observe(chapter));
    const published = JSON.parse($("#company-document").textContent);
    const key = "research-atlas:v22:" + code + ":" + published.digest;
    const segments = all("[data-prose]");
    const saved = () => {
        try { return JSON.parse(localStorage.getItem(key) || "null"); }
        catch { return null; }
    };
    const status = $("#revision");
    const toggle = $("#edit-toggle");
    const startEdit = active => {
        document.body.classList.toggle("editing", active);
        segments.forEach(segment => {
            if (active) segment.setAttribute("contenteditable", "plaintext-only");
            else segment.removeAttribute("contenteditable");
        });
        toggle.setAttribute("aria-pressed", String(active));
        toggle.textContent = active ? "结束编辑" : "编辑本地草稿";
        $("#save-draft").disabled = !active;
    };
    const changes = () => Object.fromEntries(segments.filter(
        item => item.textContent !== published.paragraphs[item.id]
    ).map(item => [item.id, item.textContent]));
    const prior = saved();
    if (prior && prior.body) {
        segments.forEach(p => { if (Object.hasOwn(prior.body, p.id)) p.textContent = prior.body[p.id]; });
        status.textContent = "已恢复本设备的草稿。";
    }
    toggle.addEventListener("click", () => startEdit(toggle.getAttribute("aria-pressed") === "false"));
    $("#save-draft").addEventListener("click", () => {
        try {
            localStorage.setItem(key, JSON.stringify({ saved: new Date().toISOString(), body: changes() }));
            status.textContent = "草稿已保存在本设备，可重开或导出。";
        } catch { status.textContent = "此浏览器的存储不可用。可导出 JSON 草稿。"; }
    });
    $("#export-draft").addEventListener("click", () => {
        const copy = { ...published, draft: { edited: new Date().toISOString(), paragraphs: changes() } };
        const url = URL.createObjectURL(new Blob([JSON.stringify(copy, null, 2)], { type: "application/json" }));
        const file = document.createElement("a");
        file.href = url;
        file.download = code + "-atlas-draft.json";
        file.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
}
