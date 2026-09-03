/* Finding Mind — reader behaviour.
   Three jobs: render math with the book's own macros, open a referenced result
   in the margin without leaving the page, and toggle the contents drawer. */

document.addEventListener("DOMContentLoaded", function () {

  /* ---- math ------------------------------------------------------------ */
  function typeset(root) {
    if (!window.renderMathInElement) return;
    renderMathInElement(root, {
      delimiters: [
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false }
      ],
      macros: window.BOOK_MACROS || {},
      throwOnError: false,
      errorColor: "#9c130e",
      trust: true,
      strict: "ignore"
    });
  }
  if (window.renderMathInElement) typeset(document.body);
  else window.addEventListener("load", function () { typeset(document.body); });

  /* ---- contents drawer -------------------------------------------------- */
  var tog = document.getElementById("railtoggle");
  if (tog) {
    tog.addEventListener("click", function () {
      var open = document.body.classList.toggle("rail-open");
      tog.setAttribute("aria-expanded", open ? "true" : "false");
      tog.textContent = open ? "Close" : "Contents";
    });
  }
  var cur = document.querySelector(".rail-ch[aria-current]");
  if (cur) cur.scrollIntoView({ block: "center" });

  /* ---- reference previews ---------------------------------------------- */
  var margin = document.getElementById("margin");
  if (!margin) return;
  var cache = {};

  function fetchDoc(url) {
    if (cache[url]) return Promise.resolve(cache[url]);
    return fetch(url).then(function (r) { return r.text(); }).then(function (t) {
      var d = new DOMParser().parseFromString(t, "text/html");
      cache[url] = d;
      return d;
    });
  }

  function show(a) {
    var href = a.getAttribute("href");
    if (!href || href.indexOf("#") < 0) return;
    var bits = href.split("#");
    var url = bits[0] || location.pathname.split("/").pop();
    var id = bits[1];
    fetchDoc(url).then(function (doc) {
      var el = doc.getElementById(id);
      if (!el) return;
      var card = document.createElement("div");
      card.className = "mcard";
      if (/^H[1-6]$/.test(el.tagName)) {
        var ht = document.createElement("h4");
        ht.textContent = el.textContent.trim();
        card.appendChild(ht);
        var g0 = document.createElement("button");
        g0.className = "go"; g0.textContent = "Go to it";
        g0.onclick = function () { location.href = href; };
        card.appendChild(g0);
        margin.innerHTML = ""; margin.appendChild(card);
        return;
      }
      var head = el.querySelector(".thm-kind");
      var name = el.querySelector(".thm-name");
      var h = document.createElement("h4");
      h.textContent = head ? head.textContent : (el.querySelector("h2,h3,figcaption") || {}).textContent || id;
      if (name) {
        var s = document.createElement("span");
        s.className = "mname";
        s.textContent = " " + name.textContent;
        h.appendChild(s);
      }
      card.appendChild(h);
      var clone = el.cloneNode(true);
      var hdr = clone.querySelector("header");
      if (hdr) hdr.remove();
      var body = document.createElement("div");
      body.innerHTML = clone.innerHTML;
      body.querySelectorAll(".xref,.cite").forEach(function (x) {
        var sp = document.createElement("span");
        sp.className = x.className;
        sp.textContent = x.textContent;
        x.replaceWith(sp);
      });
      card.appendChild(body);
      var go = document.createElement("button");
      go.className = "go";
      go.textContent = "Go to it";
      go.onclick = function () { location.href = href; };
      card.appendChild(go);
      margin.innerHTML = "";
      margin.appendChild(card);
      typeset(card);
    });
  }

  var hoverTimer = null;
  document.querySelectorAll("main .xref").forEach(function (a) {
    a.addEventListener("mouseenter", function () {
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(function () { show(a); }, 90);
    });
    a.addEventListener("mouseleave", function () { clearTimeout(hoverTimer); });
    a.addEventListener("focus", function () { show(a); });
    a.addEventListener("click", function (ev) {
      /* on narrow screens there is no margin, so let the link navigate */
      if (getComputedStyle(margin).display === "none") return;
      ev.preventDefault();
      show(a);
    });
  });
});
