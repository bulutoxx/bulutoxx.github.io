// BULUTOXX sohbet testi hakemi (lab/bot_coach.mjs kullanır).
// Ölçütler: her cevap için {intent: doğru niyet mi, useful: faydalı/somut mu, unk: "anlamadım" mı}
const fold = s => String(s || '').toLocaleLowerCase('tr').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ı/g, 'i');
const UNK = /tam anlayamadım|kafası biraz karıştı|ters gitti|anlayamadım|anlamadım/i;
function cardsOf(html) {
  const segs = String(html || '').split(/class="bt-card(?=[ "])/).slice(1);
  return segs.map(s => {
    const title = ((/<b>(.*?)<\/b>/.exec(s) || [])[1] || '').replace(/<[^>]+>/g, '');
    const small = ((/<small>(.*?)<\/small>/.exec(s) || [])[1] || '').replace(/<[^>]+>/g, '');
    const pct = +((/<b>%(\d+)<\/b>/.exec(s) || [])[1] || 0);
    const day = (/^(Paz|Pzt|Sal|Çar|Per|Cum|Cmt)/.exec(small) || [])[1] || null;
    const lg = small.split(' · ').slice(1).join(' · ');
    return { title, small, pct, day, lg, gold: /^[^"]*gold-row/.test(s) };
  });
}
function judge(t, r, prev) {
  const c = t.c || {}, text = r.text || '', html = r.html || '', C = cardsOf(html), chips = r.chips || [];
  const unk = !text.trim() || UNK.test(text) || !!r.err;
  const daysOk = !c.day || (C.length > 0 && C.every(x => c.day.includes(x.day)));
  const has = (re) => re.test(text);
  const hasTeam = (tm) => fold(text).includes(fold(tm));
  let intent = false, useful = false;
  switch (t.k) {
    case 'tarih':
      intent = !unk && (C.length ? C.every(x => c.day.includes(x.day)) : /bulamadım|yok/i.test(text));
      useful = !unk && C.length > 0 && daysOk; break;
    case 'guvenli': {
      const min = c.minp || 70;
      intent = !unk && C.length > 0 && C.every(x => x.pct >= min);
      if (c.fresh) intent = intent && prev && !C.some(x => prev.cards.some(y => y.title === x.title));
      useful = intent && (!c.n || C.length === c.n) && daysOk; break; }
    case 'altin':
      intent = !unk && /altın/i.test(text);
      useful = intent && C.length > 0 && C.some(x => x.gold); break;
    case 'takim':
      intent = !unk && hasTeam(c.team);
      useful = intent && /%\s?\d/.test(text); break;
    case 'lig':
      intent = !unk && ((C.length > 0 && C.every(x => c.lg.test(x.lg))) || (c.allowEmpty && /bulamadım|yok/i.test(text)));
      useful = !unk && C.length > 0 && C.every(x => c.lg.test(x.lg)) && daysOk; break;
    case 'analiz':
      intent = !unk && c.teams.every(hasTeam);
      useful = intent && /%\s?\d/.test(text) && (!c.kw || c.kw.test(text)); break;
    case 'canli':
      intent = !unk && /canlı/i.test(text);
      useful = intent && /taradım|canlı maç yok|oynanan maç yok|şu an (canlı|oynanan)/i.test(text); break;
    case 'liste':
      if (c.odds) { intent = !unk && (C.length >= 2 || /oran/i.test(text)); useful = !unk && C.length >= 2 && /birlikte/i.test(text) && (!c.n || C.length === c.n); break; }
      intent = !unk && /liste/i.test(text) && C.length >= 2;
      useful = intent && (!c.n || C.length === c.n) && /birlikte tutma/i.test(text) && daysOk && (!c.lg || C.every(x => c.lg.test(x.lg))); break;
    case 'kuponum':
      intent = !unk && /listende|listen boş|listen|listende/i.test(text);
      useful = intent && (!c.nonEmpty || (C.length > 0 || / - /.test(text))); break;
    case 'ekle':
      intent = r.cpAfter - r.cpBefore === c.inc;
      useful = intent && /eklendi|ekledim/i.test(text); break;
    case 'cikar':
      intent = c.toZero ? (r.cpAfter === 0 && r.cpBefore > 0) : (r.cpBefore - r.cpAfter === c.dec);
      useful = intent && /çıkar|sildim|temiz|boşal/i.test(text); break;
    case 'karne':
      intent = !unk && /tuttu|isabet/i.test(text) && /%\s?\d/.test(text);
      useful = intent && (!/altın/i.test(t.q) || /altın/i.test(text)) && (!/güçlü/i.test(t.q) || /güçlü/i.test(text)); break;
    case 'terim':
      intent = !unk && c.kw.test(text) && (!c.kw2 || c.kw2.test(text));
      useful = intent; break;
    case 'neden':
      intent = !unk && /gol beklentisi|piyasa|olasılık/i.test(text);
      useful = intent && (c.idx == null || (prev && prev.cards[c.idx] && prev.cards[c.idx].title.split(' - ').every(hasTeam))); break;
    case 'yardim':
      intent = !unk && /<li|yazabilirsin|şunları/i.test(html + text); useful = intent; break;
    case 'apphelp':
      intent = !unk && c.kw.test(text) && (!c.kw2 || c.kw2.test(text)); useful = intent; break;
    case 'selam': intent = useful = /selam|merhaba|hoş geldin|günaydın|iyi akşamlar/i.test(text); break;
    case 'tesekkur': intent = useful = /rica|ne demek|eyvallah|ne zaman istersen/i.test(text); break;
    case 'kim': intent = useful = /Bulut/.test(text) && !unk; break;
    case 'ad': intent = useful = /Ali/.test(text); break;
    case 'kayip': intent = useful = /geçmiş olsun|üzülme|top yuvarlak/i.test(text); break;
    case 'anlamsiz': intent = C.length === 0 && chips.length >= 2; useful = intent; break;
    case 'onemli':
      intent = !unk && /öne çıkan/i.test(text);
      useful = intent && /%\s?\d/.test(text); break;
  }
  return { intent: !!intent, useful: !!useful, unk: unk && t.k !== 'anlamsiz', cards: C };
}
module.exports = { judge, cardsOf };
