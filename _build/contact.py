#!/usr/bin/env python3
"""
Contact page for the Finding Mind site.

GitHub Pages serves static files only — there is no server to receive a POST,
so a form needs a third-party endpoint. Two are wired up here; pick one by
editing FORM_ENDPOINT below.

  FormSubmit  (default)  https://formsubmit.co/<hash>
      No account. You post to https://formsubmit.co/f1r3fly.ceo@gmail.com once,
      confirm the address from the email they send, and they give you a random
      hash to use instead of the address. USE THE HASH in the deployed page —
      putting the address itself in public HTML gets it scraped within days.

  Web3Forms             https://api.web3forms.com/submit
      Free, needs an access key emailed to you at web3forms.com. Slightly
      better spam filtering; the key is public by design and carries no risk.

Both deliver to f1r3fly.ceo@gmail.com and neither requires a server.

The form degrades honestly: if JavaScript is off or the endpoint is down, the
page still shows a mailto link, so nobody is left with a dead button.
"""

FORM_ENDPOINT = "https://formsubmit.co/REPLACE_WITH_YOUR_FORMSUBMIT_HASH"
CONTACT_EMAIL = "f1r3fly.ceo@gmail.com"

PAGE = """
<div class="page">
<header class="phead"><a class="back" href="../index.html">Finding Mind</a>
<h1>Comments</h1>
<p class="lede">The book is a working draft, and the parts most likely to be wrong
are the ones marked as conjectures. Corrections, objections and questions all
reach the author directly.</p></header>

<form id="contact" class="contact" action="{endpoint}" method="POST">
  <input type="hidden" name="_subject" value="Finding Mind — comment from the website">
  <input type="hidden" name="_captcha" value="false">
  <input type="hidden" name="_template" value="table">
  <input type="text" name="_honey" style="display:none" tabindex="-1" autocomplete="off" aria-hidden="true">

  <p class="field">
    <label for="c-name">Your name</label>
    <input id="c-name" name="name" type="text" autocomplete="name" required>
  </p>
  <p class="field">
    <label for="c-email">Email <span class="hint">so the author can reply</span></label>
    <input id="c-email" name="email" type="email" autocomplete="email" required>
  </p>
  <p class="field">
    <label for="c-where">Where in the book <span class="hint">optional — a chapter,
      or a numbered result like Conjecture 66.1</span></label>
    <input id="c-where" name="location" type="text">
  </p>
  <p class="field">
    <label for="c-msg">Your comment</label>
    <textarea id="c-msg" name="message" rows="9" required></textarea>
  </p>
  <p class="submit">
    <button type="submit" class="go">Send</button>
    <span id="c-status" role="status" aria-live="polite"></span>
  </p>
</form>

<p class="fallback">The form posts through a third-party relay. If it fails, or if
you would rather not use it, write to <a href="mailto:{email}?subject=Finding%20Mind">{email}</a>
directly.</p>
</div>

<script>
(function () {{
  var f = document.getElementById('contact');
  var s = document.getElementById('c-status');
  if (!f) return;
  f.addEventListener('submit', function (ev) {{
    if (f.action.indexOf('REPLACE_WITH') > -1) return;   // not configured yet: let it post normally
    ev.preventDefault();
    s.textContent = 'Sending\\u2026';
    fetch(f.action, {{
      method: 'POST',
      body: new FormData(f),
      headers: {{ 'Accept': 'application/json' }}
    }}).then(function (r) {{
      if (!r.ok) throw new Error(r.status);
      f.reset();
      s.textContent = 'Sent. Thank you \\u2014 you will get a reply at the address you gave.';
      s.className = 'ok';
    }}).catch(function () {{
      s.innerHTML = 'That did not go through. Please email ' +
        '<a href="mailto:{email}">{email}</a> instead.';
      s.className = 'bad';
    }});
  }});
}})();
</script>
"""


def contact_html():
    return PAGE.replace("{endpoint}", FORM_ENDPOINT).replace("{email}", CONTACT_EMAIL)
