# deneme.py
# Arayuz olmadan, terminalden hizli deneme icin.
# Sentetik veri uretir, modelleri karsilastirir ve grafikleri PNG olarak kaydeder.
# Calistirmak icin:  python deneme.py

import os
import time

import data
import metrics
import models
import plots

KLASOR = "deneme_ciktilari"


def main():
    """Butun parcalari terminalde bir kere calistirip sonuclari yazdirir."""
    os.makedirs(KLASOR, exist_ok=True)

    veri = data.sentetik_uret(365, tohum=42)
    print("Uretilen kayit sayisi:", len(veri))
    print("Ilk kayit:", veri[0])

    baslangic = time.time()
    sonuclar, tahminler, test = metrics.karsilastir(veri, 30, rf_dahil=models.SKLEARN_VAR)
    print(f"Karsilastirma suresi: {time.time() - baslangic:.1f} sn\n")

    print(f"{'Model':<18}{'MAPE (%)':>10}{'MAE (MW)':>12}{'RMSE (MW)':>12}")
    for isim, m in sonuclar.items():
        print(f"{isim:<18}{m['MAPE']:>10.2f}{m['MAE']:>12.0f}{m['RMSE']:>12.0f}")
    print("\nEn iyi model:", metrics.en_iyi_model(sonuclar))

    # Grafikleri dosyaya kaydediyoruz
    grafikler = {
        "gercek_vs_tahmin.png": plots.gercek_vs_tahmin(test, tahminler),
        "sicaklik_yuk.png": plots.sicaklik_yuk(veri),
        "gunluk_profil.png": plots.gunluk_profil(veri),
        "model_karsilastirma.png": plots.model_karsilastirma(sonuclar),
    }
    onemler = models.ozellik_onemleri()
    if onemler is not None:
        grafikler["ozellik_onemi.png"] = plots.ozellik_onemi(onemler)

    for isim, figur in grafikler.items():
        figur.savefig(os.path.join(KLASOR, isim))
    print("Grafikler", KLASOR, "klasorune kaydedildi.")


if __name__ == "__main__":
    main()
