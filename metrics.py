# metrics.py
# Modelleri degerlendirme: egitim/test ayrimi, MAPE, MAE, RMSE ve karsilastirma.

import math

import models

# Haftalik profilin 4 hafta geriye bakabilmesi icin egitimde en az bu kadar saat olmali
EN_AZ_EGITIM_SAATI = 168 * 4


def mape(gercekler, tahminler):
    """Ortalama mutlak yuzde hatayi (%) hesaplar."""
    toplam = 0.0
    sayac = 0
    for g, t in zip(gercekler, tahminler):
        if g == 0:
            # Sifira bolme olmasin diye gercegi 0 olan saatleri atliyoruz
            continue
        toplam += abs(g - t) / abs(g)
        sayac += 1
    if sayac == 0:
        raise ValueError("MAPE hesaplanamadı: tüm gerçek değerler sıfır.")
    return toplam / sayac * 100


def mae(gercekler, tahminler):
    """Ortalama mutlak hatayi (MW) hesaplar."""
    if len(gercekler) == 0:
        raise ValueError("MAE için veri yok.")
    toplam = 0.0
    for g, t in zip(gercekler, tahminler):
        toplam += abs(g - t)
    return toplam / len(gercekler)


def rmse(gercekler, tahminler):
    """Hata karelerinin ortalamasinin karekokunu (MW) hesaplar."""
    if len(gercekler) == 0:
        raise ValueError("RMSE için veri yok.")
    toplam = 0.0
    for g, t in zip(gercekler, tahminler):
        toplam += (g - t) ** 2
    return math.sqrt(toplam / len(gercekler))


def egitim_test_ayir(veri, test_gun=30):
    """Son test_gun gunu test, oncesini egitim olarak ayirir."""
    test_saat = test_gun * 24
    if len(veri) < test_saat + EN_AZ_EGITIM_SAATI:
        gereken_gun = test_gun + EN_AZ_EGITIM_SAATI // 24
        raise ValueError(
            f"Veri yetersiz: {test_gun} günlük test için en az {gereken_gun} günlük "
            f"veri gerekiyor, sizde {len(veri) // 24} gün var."
        )
    egitim = veri[:-test_saat]
    test = veri[-test_saat:]
    return egitim, test


def karsilastir(veri, test_gun=30, rf_dahil=False):
    """Tum modelleri test doneminde calistirir; (sonuclar, tahminler, test) dondurur."""
    egitim, test = egitim_test_ayir(veri, test_gun)

    # Regresyon ve RF sadece egitim verisiyle egitiliyor, test verisini gormuyor
    models.hazirla(egitim, rf_dahil)
    modeller = models.model_listesi(rf_dahil)

    # Her model icin tahmin listesi
    tahminler = {}
    for isim in modeller:
        tahminler[isim] = []
    gercekler = []

    baslangic = len(egitim)
    for i in range(baslangic, len(veri)):
        hedef = veri[i]
        # Persistence ve haftalik model gercek hayattaki gibi
        # bir onceki gunun gercek degerlerini kullanabiliyor
        gecmis = veri[:i]
        gercekler.append(hedef["yuk"])
        for isim, fonksiyon in modeller.items():
            tahminler[isim].append(fonksiyon(gecmis, hedef))

    sonuclar = {}
    for isim in modeller:
        sonuclar[isim] = {
            "MAPE": mape(gercekler, tahminler[isim]),
            "MAE": mae(gercekler, tahminler[isim]),
            "RMSE": rmse(gercekler, tahminler[isim]),
        }
    return sonuclar, tahminler, test


def en_iyi_model(sonuclar):
    """MAPE'si en dusuk modelin adini dondurur."""
    en_iyi = None
    for isim, metrik in sonuclar.items():
        if en_iyi is None or metrik["MAPE"] < sonuclar[en_iyi]["MAPE"]:
            en_iyi = isim
    return en_iyi
