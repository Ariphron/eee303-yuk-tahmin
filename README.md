# EEE303 - Elektrik Yük Tahmin Aracı

Saatlik elektrik tüketimini (yük, MW) geçmiş veri, saat, gün tipi ve sıcaklıktan tahmin eden
Tkinter arayüzlü bir Python uygulaması. Kısa vadeli yük tahmini (STLF) problemini basit
modellerle ele alıp modelleri MAPE / MAE / RMSE ile karşılaştırıyor.

## Kurulum

Python 3.9 veya üstü gerekiyor.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`scikit-learn` sadece bonus Random Forest modeli için. Yüklü değilse program yine çalışır,
sadece RF seçeneği kapalı görünür.

> **macOS notu:** macOS ile gelen `/usr/bin/python3` eski bir Tk (8.5) kullanıyor ve yeni macOS
> sürümlerinde pencere açılırken donabiliyor. Bu durumda Homebrew ile
> `brew install python-tk@3.12` kurup sanal ortamı `python3.12 -m venv .venv` ile oluşturun.

## Çalıştırma

```bash
python main.py      # arayüz
python deneme.py    # arayüzsüz hızlı deneme (sonuçları terminale yazar, grafikleri PNG kaydeder)
```

## Dosya yapısı

```
yuk_tahmin/
├── main.py        # Tkinter arayüzü, 4 sekme
├── data.py        # sentetik veri üretimi, CSV okuma/yazma
├── models.py      # persistence, haftalık profil, regresyon, Random Forest
├── metrics.py     # MAPE/MAE/RMSE, eğitim-test ayrımı, karşılaştırma
├── plots.py       # tüm matplotlib grafikleri (hepsi Figure döndürür)
├── utils.py       # girdi doğrulama fonksiyonları
├── deneme.py      # terminalden deneme
└── data/          # örnek CSV dosyaları
```

## Sekmeler

| Sekme | Ne yapıyor |
|---|---|
| Veri | Sentetik veri üretme veya CSV yükleme, bozuk satır raporu, veri tablosu |
| Keşif | Günlük profil, sıcaklık-yük saçılımı, gün bazında ortalama, yıllık seyir |
| Tahmin | Tarih, saat ve sıcaklık girilir; modellerin tahmini yan yana gösterilir |
| Karşılaştırma | Son N gün test edilir; MAPE/MAE/RMSE tablosu, grafikler, CSV/PNG kaydetme |

## Modeller

Hepsi aynı imzaya sahip: `model(gecmis, hedef) -> float`

1. **Persistence:** 24 saat önceki yük.
2. **Haftalık profil:** 1, 2, 3 ve 4 hafta önceki aynı saatin ortalaması.
3. **Sıcaklık regresyonu:** Veri (saat, hafta_sonu) çiftine göre 48 gruba ayrılır, her grup için
   `numpy.polyfit` ile `yuk = a·T² + b·T + c` bulunur.
4. **Random Forest (bonus):** sklearn, özellikler: saat, gün, sıcaklık, 24 saat önceki yük.

Sentetik veriyle (365 gün, son 30 gün test) aldığımız sonuçlar:

| Model | MAPE (%) | MAE (MW) | RMSE (MW) |
|---|---|---|---|
| Persistence | 6.05 | 2165 | 2894 |
| Haftalık profil | 3.41 | 1233 | 1517 |
| Regresyon | 1.48 | 538 | 685 |
| Random Forest | 1.73 | 618 | 798 |

Persistence hafta sonu / hafta içi geçişlerinde büyük hata yapıyor (pazartesiyi pazara göre
tahmin ediyor). Haftalık profil bu sorunu çözüyor ama sıcaklık değişimini görmüyor. Regresyon
sıcaklığı da kullandığı için en iyi sonucu veriyor. Sentetik veri zaten sıcaklığa bağlı bir
formülle üretildiği için regresyonun bu kadar iyi çıkması beklenen bir sonuç.

## CSV formatı

```
tarih,sicaklik,yuk
2024-01-01 00:00,1.5,31428.5
2024-01-01 01:00,0.7,31184.0
```

`data/` klasöründe hata kontrolünü denemek için örnek dosyalar var:

- `ornek_veri.csv` : 365 günlük düzgün veri
- `bozuk_ornek.csv` : 60 günlük veri, içinde 5 tane bozuk satır var (atlanır ve raporlanır)
- `yanlis_sutun.csv` : sütun adları yanlış
- `bos.csv` : boş dosya
