# utils.py
# Girdi dogrulama fonksiyonlari. Arayuzdeki butun girisler buradan geciyor,
# boylece programi cokertebilecek girdiler tek bir yerde kontrol ediliyor.
# Her fonksiyon (deger, hata_mesaji) seklinde iki deger dondurur.
# Hata yoksa mesaj bos string, hata varsa deger None olur.

import os
from datetime import datetime


def sayi_al(metin, alt, ust):
    """Metni sayiya cevirir; hata varsa (None, mesaj) doner."""
    metin = metin.strip()
    if metin == "":
        return None, "Bu alan boş bırakılamaz."
    try:
        deger = float(metin.replace(",", "."))
    except ValueError:
        return None, "Lütfen bir sayı girin."
    if not alt <= deger <= ust:
        return None, f"Değer {alt} ile {ust} arasında olmalı."
    return deger, ""


def tam_sayi_al(metin, alt, ust):
    """Metni tam sayiya cevirir; ondalikli veya aralik disi ise hata doner."""
    deger, hata = sayi_al(metin, alt, ust)
    if hata:
        return None, hata
    if deger != int(deger):
        return None, "Lütfen tam sayı girin."
    return int(deger), ""


def tarih_al(metin):
    """GG.AA.YYYY veya YYYY-AA-GG bicimindeki metni tarihe cevirir."""
    metin = metin.strip()
    if metin == "":
        return None, "Tarih boş bırakılamaz."
    for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(metin, fmt), ""
        except ValueError:
            pass
    return None, "Tarih GG.AA.YYYY biçiminde olmalı (örn. 31.12.2024)."


def dosya_kontrol(yol):
    """Dosyanin var olup olmadigini ve CSV olup olmadigini kontrol eder."""
    if not yol:
        return None, "Dosya seçilmedi."
    if not os.path.isfile(yol):
        return None, "Dosya bulunamadı."
    if not yol.lower().endswith(".csv"):
        return None, "Lütfen .csv uzantılı bir dosya seçin."
    if os.path.getsize(yol) == 0:
        return None, "Seçilen dosya boş."
    return yol, ""


def mw_yaz(deger):
    """Sayiyi binlik ayiracli MW metnine cevirir (orn. 41.250 MW)."""
    return f"{deger:,.0f} MW".replace(",", ".")


def tarih_yaz(tarih):
    """datetime'i ekranda gosterilecek GG.AA.YYYY SS:DD bicimine cevirir."""
    return tarih.strftime("%d.%m.%Y %H:%M")
