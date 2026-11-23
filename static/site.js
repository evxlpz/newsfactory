(function () {
  // Поширення: нативне меню телефона (Instagram, сторіс, будь-які застосунки) + копіювання посилання
  document.querySelectorAll('.share').forEach(function (box) {
    var url = box.dataset.url, title = box.dataset.title;
    var nat = box.querySelector('.sh-native');
    if (nat) {
      if (navigator.share) {
        nat.addEventListener('click', function () { navigator.share({ title: title, url: url }).catch(function () {}); });
      } else { nat.classList.add('hide'); }
    }
    var copy = box.querySelector('.sh-copy');
    if (copy) copy.addEventListener('click', function () {
      var done = function () { copy.classList.add('ok'); copy.setAttribute('title', box.dataset.copied); setTimeout(function () { copy.classList.remove('ok'); }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () {});
    });
  });

  // Плашка «Читати вашою мовою», якщо мова браузера є серед версій сторінки
  var bar = document.getElementById('langbar');
  if (bar) {
    var cur = document.documentElement.lang;
    var want = (navigator.languages || [navigator.language || '']).map(function (l) { return (l || '').slice(0, 2).toLowerCase(); });
    var dismissed = false;
    try { dismissed = localStorage.getItem('nf_lang_dismiss') === '1'; } catch (e) { dismissed = false; }
    if (!dismissed && want.length && want[0] !== cur) {
      var a = bar.querySelector('a[hreflang="' + want[0] + '"]');
      if (a) {
        bar.querySelectorAll('a').forEach(function (x) { if (x !== a) x.remove(); });
        bar.hidden = false;
        bar.querySelector('button').addEventListener('click', function () {
          bar.hidden = true;
          try { localStorage.setItem('nf_lang_dismiss', '1'); } catch (e) { /* приватний режим — просто ховаємо */ }
        });
      }
    }
  }
})();
