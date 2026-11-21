# data.py
# Veri ile ilgili her sey burada: sentetik veri uretme, CSV okuma/yazma.
# Her kayit bir dict, butun veri bu dict'lerin saat sirasina gore listesi.
# {"tarih": datetime, "saat": 14, "gun": 2, "hafta_sonu": False,
#  "sicaklik": 31.5, "yuk": 41250.0}

import csv
import math
import os
import random
from datetime import datetime, timedelta

# Saat basina yuk carpani (0 -> 00:00, 23 -> 23:00)
# Gece 04:00 en dusuk, sabah artiyor, aksam 20:00 civari puant
SAAT_PROFILI = [
    0.80, 0.76, 0.73, 0.71, 0.70, 0.72,   # 00-05
    0.78, 0.87, 0.96, 1.01, 1.03, 1.04,   # 06-11
    1.02, 1.01, 1.02, 1.02, 1.03, 1.06,   # 12-17
    1.10, 1.13, 1.15, 1.12, 1.03, 0.90,   # 18-23
]

# Resmi tatiller (ay, gun): isim -> bu gunlerde yuk hafta sonu gibi dusuk
TATILLER = {
    (1, 1): "Yilbasi",
    (4, 23): "Ulusal Egemenlik ve Cocuk Bayrami",
    (5, 1): "Emek ve Dayanisma Gunu",
    (5, 19): "Ataturk'u Anma, Genclik ve Spor Bayrami",
    (7, 15): "Demokrasi ve Milli Birlik Gunu",
    (8, 30): "Zafer Bayrami",
    (10, 29): "Cumhuriyet Bayrami",
}

GUN_ISIMLERI = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"]

# Sentetik veri parametreleri
BAZ_YUK = 33000.0        # MW, ortalama bir saatin yuku
ISITMA_KATSAYISI = 550.0  # 18 derecenin altinda her derece icin eklenen MW
SOGUTMA_KATSAYISI = 900.0  # 22 derecenin ustunde her derece icin eklenen MW

CSV_SUTUNLARI = ["tarih", "sicaklik", "yuk"]
TARIH_FORMATI = "%Y-%m-%d %H:%M"


def kayit_olustur(tarih, sicaklik, yuk):
    """Verilen tarih, sicaklik ve yukten sozlesmeye uygun bir kayit dict'i olusturur."""
    gun = tarih.weekday()
    return {
        "tarih": tarih,
        "saat": tarih.hour,
        "gun": gun,
        "hafta_sonu": gun >= 5,
        "sicaklik": sicaklik,
        "yuk": yuk,
    }


def tatil_mi(tarih):
    """Tarih resmi tatil gunuyse True dondurur."""
    return (tarih.month, tarih.day) in TATILLER


def sicaklik_uret(tarih):
    """Yillik ve gunluk sinusler + gurultu ile bir saatin sicakligini uretir."""
    gun_no = tarih.timetuple().tm_yday
    # Yillik aci: Ocak ortasinda dip, Temmuz ortasinda tepe olacak sekilde kaydirdik
    yillik_aci = 2 * math.pi * (gun_no - 105) / 365
    # Gunluk aci: en sicak saat 15:00 olsun (sin'in tepesi 15'e gelsin)
    gunluk_aci = 2 * math.pi * (tarih.hour - 9) / 24
    sicaklik = 15 + 10 * math.sin(yillik_aci) + 5 * math.sin(gunluk_aci)
    sicaklik += random.gauss(0, 1.5)
    return round(sicaklik, 1)


def yuk_uret(tarih, sicaklik):
    """Saat profili, gun carpani ve sicaklik etkisinden bir saatin yukunu uretir."""
    if tarih.weekday() >= 5 or tatil_mi(tarih):
        gun_carpani = 0.85
    else:
        gun_carpani = 1.0

    yuk = BAZ_YUK * SAAT_PROFILI[tarih.hour] * gun_carpani
    yuk += ISITMA_KATSAYISI * max(0, 18 - sicaklik)   # isitma etkisi
    yuk += SOGUTMA_KATSAYISI * max(0, sicaklik - 22)  # klima etkisi
    yuk += random.gauss(0, 500)                        # gurultu
    return round(yuk, 1)


def sentetik_uret(gun_sayisi=365, baslangic=None, tohum=None):
    """gun_sayisi x 24 saatlik sentetik sicaklik ve yuk verisi uretir."""
    if tohum is not None:
        random.seed(tohum)
    if baslangic is None:
        baslangic = datetime(2024, 1, 1, 0, 0)

    veri = []
    for i in range(gun_sayisi * 24):
        tarih = baslangic + timedelta(hours=i)
        sicaklik = sicaklik_uret(tarih)
        yuk = yuk_uret(tarih, sicaklik)
        veri.append(kayit_olustur(tarih, sicaklik, yuk))
    return veri


def tarih_coz(metin):
    """CSV'deki tarih metnini datetime'a cevirir, birkac farkli formati dener."""
    formatlar = [TARIH_FORMATI, "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"]
    for fmt in formatlar:
        try:
            return datetime.strptime(metin.strip(), fmt)
        except ValueError:
            pass
    raise ValueError("tarih okunamadi: " + metin)


def csv_oku(yol):
    """CSV dosyasini okur, bozuk satirlari atlar; (veri, atlanan_sayisi) dondurur."""
    if not os.path.exists(yol):
        raise FileNotFoundError(f"Dosya bulunamadı: {yol}")

    veri = []
    atlanan = 0
    gorulen_tarihler = set()

    with open(yol, "r", encoding="utf-8-sig", newline="") as dosya:
        okuyucu = csv.DictReader(dosya)
        if okuyucu.fieldnames is None:
            raise ValueError("Dosya boş.")

        # Sutun adlarini kucuk harfe cevirip bosluklari temizliyoruz
        sutunlar = [s.strip().lower() for s in okuyucu.fieldnames]
        eksikler = [s for s in CSV_SUTUNLARI if s not in sutunlar]
        if eksikler:
            raise ValueError(
                "CSV'de gerekli sütunlar yok: " + ", ".join(eksikler)
                + "\nDosyadaki sütunlar: " + ", ".join(sutunlar)
                + "\nBeklenen sütunlar: tarih, sicaklik, yuk"
            )
        okuyucu.fieldnames = sutunlar

        for satir in okuyucu:
            try:
                tarih = tarih_coz(satir["tarih"])
                sicaklik = float(satir["sicaklik"].replace(",", "."))
                yuk = float(satir["yuk"].replace(",", "."))
            except (ValueError, AttributeError, KeyError):
                # AttributeError: eksik sutunlu satirlarda deger None geliyor
                atlanan += 1
                continue

            # Mantiksiz degerleri de bozuk sayiyoruz
            if yuk <= 0 or not -50 <= sicaklik <= 60 or tarih in gorulen_tarihler:
                atlanan += 1
                continue

            gorulen_tarihler.add(tarih)
            veri.append(kayit_olustur(tarih, sicaklik, yuk))

    if len(veri) == 0:
        raise ValueError("Dosyada hiç geçerli satır bulunamadı.")

    # Saat sirasina gore diziyoruz, dosya karisik sirada olabilir
    veri.sort(key=lambda k: k["tarih"])
    return veri, atlanan


def csv_kaydet(veri, yol):
    """Veriyi tarih, sicaklik, yuk sutunlariyla CSV dosyasina yazar."""
    with open(yol, "w", encoding="utf-8", newline="") as dosya:
        yazici = csv.writer(dosya)
        yazici.writerow(CSV_SUTUNLARI)
        for kayit in veri:
            yazici.writerow([
                kayit["tarih"].strftime(TARIH_FORMATI),
                kayit["sicaklik"],
                kayit["yuk"],
            ])


def eksik_saat_sayisi(veri):
    """Ilk ve son kayit arasinda kac saatin eksik oldugunu hesaplar."""
    if len(veri) < 2:
        return 0
    toplam_saat = int((veri[-1]["tarih"] - veri[0]["tarih"]).total_seconds() // 3600) + 1
    return toplam_saat - len(veri)


def veri_ozeti(veri):
    """Veri sekmesindeki rapor icin ozet bilgileri dict olarak dondurur."""
    yukler = [k["yuk"] for k in veri]
    sicakliklar = [k["sicaklik"] for k in veri]
    return {
        "kayit": len(veri),
        "baslangic": veri[0]["tarih"],
        "bitis": veri[-1]["tarih"],
        "gun": len(veri) / 24,
        "eksik_saat": eksik_saat_sayisi(veri),
        "yuk_min": min(yukler),
        "yuk_max": max(yukler),
        "yuk_ort": sum(yukler) / len(yukler),
        "sic_min": min(sicakliklar),
        "sic_max": max(sicakliklar),
    }
