# Pdf2 — Belge Atölyesi

PDF belgelerini Word (.docx) ve Excel (.xlsx) biçimine dönüştüren, taranmış
belgeleri OCR ile okuyan ve gerektiğinde belgeyi düzenlemenizi sağlayan
Windows masaüstü uygulaması.

## Özellikler

- **PDF → Word:** Yerleşimi koruyan dönüşüm (pdf2docx). Taranmış sayfalar OCR ile
  metne çevrilir; karma belgelerde dijital sayfalar yerleşimli, taranmış sayfalar
  OCR metni olarak aktarılır.
- **PDF → Excel:** Tablo tespiti (PyMuPDF + pdfplumber birlikte, en iyi sonuç
  seçilir), sayı/tarih dönüşümü, sayfa başına ayrı sekme veya tek sekme düzeni.
  Tablo bulunamayan sayfalar tek sütun metin olarak aktarılır.
- **OCR:** Tesseract kuruluysa onunla (en iyi Türkçe kalitesi), değilse gömülü
  RapidOCR/ONNX ile çalışır. Motor ve dil ayarlardan seçilebilir.
- **PDF Düzenle:** Kapsamlı düzenleme sekmesi:
  - Geri al / ileri al (Ctrl+Z / Ctrl+Y), metin seçme ve kopyalama (Ctrl+C)
  - Sayfa işlemleri: döndürme, silme, taşıma, PDF ekleme, aralıklara bölme
  - İçerik: vurgu, metin ve not ekleme; beyazlatma ve kalıcı silme (redaksiyon);
    seçili metni düzenleme (punto/renk korunur, font yaklaşık)
  - Çizim: serbest kalem, dikdörtgen, elips, çizgi, ok (renk/kalınlık seçimli)
  - Görsel ve imza ekleme (pano veya dosyadan, oran korumalı)
  - Filigran ve sayfa numarası (tüm sayfalara veya geçerli sayfaya)
  - Küçük resim paneli: sürükle-bırak sıralama, çoklu seçim, toplu döndür/sil,
    çoğalt, kopyala/kes/yapıştır
  - Kırpma (CropBox) ve sıfırlama; sayfa çoğaltma
  - Şifre ekleme/kaldırma (AES-256, yazdırma/kopyalama izinleri) ve
    parola korumalı PDF açma; form alanlarını listeleme ve doldurma
- **Çıktı Düzenle:** Dönüştürülen Word/Excel dosyalarında paragraf, tablo hücresi
  ve hücre düzenleme; "Uygulamada aç" ile Word/Excel'de açma.
- **Arayüz:** Türkçe, sürükle-bırak destekli, dönüşüm sırasında donmayan
  (QThread) ilerleme takibi.

## Kurulum

Python 3.12 gerekir (3.13/3.14 bazı bağımlılıklarda sorun çıkarabilir).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Çalıştırma

```powershell
# Masaüstü arayüzü
.\.venv\Scripts\python.exe -m app

# Komut satırı
.\.venv\Scripts\python.exe -m app.cli belge.pdf --to word --out cikti
.\.venv\Scripts\python.exe -m app.cli belge.pdf --to excel --pages 1-3,5
.\.venv\Scripts\python.exe -m app.cli --help
```

CLI seçenekleri: `--to word|excel`, `--pages`, `--out`, `--no-ocr`,
`--force-ocr`, `--ocr-engine auto|tesseract|rapidocr`, `--ocr-lang`,
`--layout page_per_sheet|all_in_one`.

## OCR

- **RapidOCR** gömülüdür, ek kurulum gerektirmez.
- **Tesseract** (isteğe bağlı, daha iyi Türkçe doğruluğu): Tesseract kurun,
  `tesseract.exe` PATH'te olsun ve `tur` dil verisini yükleyin. Kuruluysa
  "Otomatik" seçiminde Tesseract tercih edilir.

## Testler

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Paketleme (.exe)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\pyinstaller.exe packaging\pdf2.spec
```

Çıktı: `dist\Pdf2\Pdf2.exe`. Tesseract gömülmez; kurulumlu makinede opsiyonel
olarak kullanılır, yoksa RapidOCR devreye girer.

Paketlenmiş .exe tanılama (konsol çıktısı yoktur; çıkış kodu ve üretilen dosya kontrol edilir):

```powershell
$env:PDF2_CLI = "belge.pdf --to word --out cikti"   # .exe'yi CLI olarak çalıştırır
$env:PDF2_SMOKE = "1"                                # arayüzü açıp 2 sn sonra kapatır
```

## Mimari

```
app/
  main.py                 GUI girişi
  cli.py                  Komut satırı girişi
  workers.py              QThread dönüşüm işçisi
  core/
    models.py             Dönüşüm seçenekleri ve sonuç modelleri
    pipeline.py           Dönüşüm orkestrasyonu
    utils.py              Sayfa aralığı, sayı ayrıştırma
    converter/            pdf_to_word, pdf_to_excel, ocr, scanned_detector, docx_fixups
    pdf_editor/           PdfEditSession: page_ops, annotate, text_tools, draw_tools,
                          image_tools, stamp_tools, form_tools
    output_editor/        Word/Excel düzenleyicileri
  ui/                     PySide6 sekmeleri, tema token'ları (theme.py),
                          küçük resim paneli, diyaloglar
```

Tasarım sistemi `app/ui/theme.py` içindeki token'lardan beslenir; yeni stiller
sabit renk kodu yerine bu token'ları kullanmalıdır.

## Lisans notu

Bu uygulama pdf2docx ve PyMuPDF (AGPL v3) kullanır. Kişisel/iç kullanımda
sorun yoktur; yazılımı dağıtırsanız AGPL v3 koşulları geçerlidir. Tesseract
(Apache 2.0), RapidOCR (Apache 2.0), python-docx ve openpyxl (MIT) ayrı
lisanslara tabidir.
