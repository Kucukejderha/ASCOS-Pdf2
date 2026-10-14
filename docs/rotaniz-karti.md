# rotaniz.com — ASCOS Pdf2 kartı

Durum: **YAYINDA** (2026-10-14, REST API ile eklendi) · Sürüm: v0.1.3
Sayfa: https://rotaniz.com/ascos-araclar/ (WordPress sayfa ID 15)

Kart snippet'i: `docs/ascos-araclar-pdf2-karti.html` (site ile birebir aynı
`ascos-tool-card` yapısı; DbMount kartından sonra, "Yeni ASCOS araçları…"
notunun hemen üstüne eklendi).

Kart görseli: Şimdilik CSS ile üretilmiş geçici "PDF2" kutusu kullanılıyor
(yükleme gerektirmez, aile renklerinde). Gerçek logo hazır olduğunda ikon
bloğundaki `<div class="ascos-tool-icon" style="...">PDF2</div>` yerine
`<img class="ascos-tool-icon" src="…/ASCOS-Pdf2-web.png">` konularak değiştirilir.

## Bağlantılar

| Amaç | Bağlantı |
|---|---|
| **MSI indir (önerilen, her sürümde çalışır)** | https://github.com/Kucukejderha/ASCOS-Pdf2/releases/latest/download/ASCOS-Pdf2-latest.msi |
| Taşınabilir zip (sürümlü) | https://github.com/Kucukejderha/ASCOS-Pdf2/releases/download/v0.1.3/ASCOS-Pdf2-v0.1.3-win64.zip |
| Sürüm sayfası (GitHub) | https://github.com/Kucukejderha/ASCOS-Pdf2/releases/tag/v0.1.3 |
| Kaynak kod | https://github.com/Kucukejderha/ASCOS-Pdf2 |

Not: `latest/download/ASCOS-Pdf2-latest.msi` bağlantısı her yeni sürümde kendiliğinden
güncel MSI'ı gösterir; **sayfayı her sürümde güncellemek gerekmez**. Zip bağlantısı
sürüm adı içerdiği için yeni sürümde değiştirilmelidir (zip ikinci seçenek olarak
sayfada kalabilir veya çıkarılabilir).

## Bakım notları

- Site güncellemesi için kullanılan WP uygulama şifresi iş sonrası **iptal
  edilmelidir** (Kullanıcılar → Profil → Uygulama Şifreleri).
- `ASCOS Rotaniz.com` reposundaki `backup/rotaniz-db-backup.sql` **bozuk**
  (dosyadaki `%` karakterleri `{605a2e65…}` jetonuna dönüşmüş); geri yükleme
  akışından önce yedeğin yeniden alınması gerekir.


## Kart metni (site düzeniyle aynı biçim)

```markdown
WINDOWSÜCRETSİZAGPL V3

## ASCOS Pdf2

PDF belgelerinizi Word ve Excel'e dönüştürün; taranmış belgelerin tabloları
düzeni bozulmadan aktarılsın. Belgelerinizi uygulama içinde düzenleyin: sayfa
işlemleri, metin düzenleme, çizim ve imza, filigran, sayfa numarası, kırpma,
form doldurma ve şifreleme.

- PDF → Word ve PDF → Excel dönüşümü (tablolar ve yerleşim korunur)
- Taranmış belgelerde OCR ile tablo yapısı gerçek Word tablosu olarak çıkarılır
- PDF düzenleme: geri al/ileri al, metin düzenleme, silgi/redaksiyon, kalem ve
  şekiller, görsel/imza ekleme, filigran, sayfa numarası, kırpma, sayfa sıralama
- Şifre koruması ekleme/kaldırma ve form alanlarını doldurma
- Word/Excel çıktılarını düzenleme ve tek tıkla Word/Excel'de açma
- Türkçe arayüz; kurulum gerektirmeyen taşınabilir (zip) sürüm de mevcut

[ASCOS Pdf2'yi indir ↓](https://github.com/Kucukejderha/ASCOS-Pdf2/releases/latest/download/ASCOS-Pdf2-latest.msi)
Windows 10/11 • MSI kurulum (yönetici gerekmez) • 138 MB • AGPL v3 • v0.1.3
```

## HTML sürümü (WordPress blok/özel HTML için)

```html
<h2>ASCOS Pdf2</h2>
<p>PDF belgelerinizi Word ve Excel'e dönüştürün; taranmış belgelerin tabloları
düzeni bozulmadan aktarılsın. Belgelerinizi uygulama içinde düzenleyin: sayfa
işlemleri, metin düzenleme, çizim ve imza, filigran, sayfa numarası, kırpma,
form doldurma ve şifreleme.</p>
<ul>
  <li>PDF → Word ve PDF → Excel dönüşümü (tablolar ve yerleşim korunur)</li>
  <li>Taranmış belgelerde OCR ile tablo yapısı gerçek Word tablosu olarak çıkarılır</li>
  <li>PDF düzenleme: geri al/ileri al, metin düzenleme, silgi/redaksiyon, kalem ve şekiller,
      görsel/imza ekleme, filigran, sayfa numarası, kırpma, sayfa sıralama</li>
  <li>Şifre koruması ekleme/kaldırma ve form alanlarını doldurma</li>
  <li>Word/Excel çıktılarını düzenleme ve tek tıkla Word/Excel'de açma</li>
  <li>Türkçe arayüz; taşınabilir (zip) sürüm de mevcut</li>
</ul>
<p>
  <a href="https://github.com/Kucukejderha/ASCOS-Pdf2/releases/latest/download/ASCOS-Pdf2-latest.msi">ASCOS Pdf2'yi indir ↓</a><br>
  <small>Windows 10/11 • MSI kurulum (yönetici gerekmez) • 138 MB • AGPL v3 • v0.1.3</small>
</p>
```
