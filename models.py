# models.py
# Tahmin modelleri. Hepsinin imzasi ayni:
#     def model(gecmis: list[dict], hedef: dict) -> float
# gecmis: hedeften onceki kayitlar, hedef: yuku tahmin edilecek saat
# Bu sayede arayuz ve metrics.py modelleri bir sozlukte tutup donguyle calistirabiliyor.

import numpy as np

# sklearn yoksa program yine calissin, sadece RF modeli gizlensin
try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_VAR = True
except ImportError:
    SKLEARN_VAR = False

# Haftalik profilde kac hafta geriye bakilacak
HAFTA_SAYISI = 4

# Egitilen modellerin katsayilari burada saklaniyor.
# Regresyonu ve RF'yi her saat icin bastan egitmek cok yavas oldugu icin
# hazirla() fonksiyonu bir kere egitip buraya koyuyor.
egitilmis = {"veri": None, "katsayilar": None, "araliklar": None, "rf": None}


def onceki_kayit(gecmis, hedef, kac_saat):
    """Hedeften kac_saat once olan kaydi gecmiste bulur, yoksa None dondurur."""
    if len(gecmis) == 0:
        return None
    aranan = hedef["tarih"].timestamp() - kac_saat * 3600
    son = gecmis[-1]["tarih"].timestamp()

    # Veri saatlik ve eksiksizse kaydin indeksi direkt hesaplanabilir
    fark = int(round((son - aranan) / 3600))
    indeks = len(gecmis) - 1 - fark
    if 0 <= indeks < len(gecmis) and gecmis[indeks]["tarih"].timestamp() == aranan:
        return gecmis[indeks]

    # Veride eksik saat varsa indeks kayar, o zaman geriye dogru tek tek ariyoruz
    for kayit in reversed(gecmis):
        zaman = kayit["tarih"].timestamp()
        if zaman == aranan:
            return kayit
        if zaman < aranan:
            break
    return None


# ---------------------------------------------------------------------------
# 1) Persistence: yarin bugunun aynisi olur
# ---------------------------------------------------------------------------
def persistence(gecmis, hedef):
    """24 saat onceki yuku tahmin olarak dondurur."""
    kayit = onceki_kayit(gecmis, hedef, 24)
    if kayit is None:
        raise ValueError("Persistence için 24 saat önceki veri yok.")
    return kayit["yuk"]


# ---------------------------------------------------------------------------
# 2) Haftalik profil: son 4 haftanin ayni gun ve saatinin ortalamasi
# ---------------------------------------------------------------------------
def haftalik(gecmis, hedef):
    """Son 4 haftanin ayni gun ve saatindeki yuklerin ortalamasini dondurur."""
    degerler = []
    for hafta in range(1, HAFTA_SAYISI + 1):
        kayit = onceki_kayit(gecmis, hedef, 168 * hafta)  # 168 saat = 1 hafta
        if kayit is not None:
            degerler.append(kayit["yuk"])

    if len(degerler) == 0:
        # Bir hafta bile gecmis yoksa persistence'a donuyoruz
        return persistence(gecmis, hedef)
    return sum(degerler) / len(degerler)


# ---------------------------------------------------------------------------
# 3) Sicaklik regresyonu: her (saat, hafta_sonu) grubu icin
#    yuk = a*T^2 + b*T + c  egrisi numpy.polyfit ile bulunur
# ---------------------------------------------------------------------------
def regresyon_egit(gecmis):
    """Her (saat, hafta_sonu) grubu icin 2. derece polinom katsayilarini hesaplar."""
    # Once kayitlari gruplara ayiriyoruz: 24 saat x 2 gun tipi = 48 grup
    gruplar = {}
    for kayit in gecmis:
        anahtar = (kayit["saat"], kayit["hafta_sonu"])
        if anahtar not in gruplar:
            gruplar[anahtar] = {"sicaklik": [], "yuk": []}
        gruplar[anahtar]["sicaklik"].append(kayit["sicaklik"])
        gruplar[anahtar]["yuk"].append(kayit["yuk"])

    katsayilar = {}
    araliklar = {}
    for anahtar, grup in gruplar.items():
        # 2. derece polinom icin en az 3 nokta lazim
        if len(grup["yuk"]) >= 3:
            katsayilar[anahtar] = np.polyfit(grup["sicaklik"], grup["yuk"], 2)
            araliklar[anahtar] = (min(grup["sicaklik"]), max(grup["sicaklik"]))
    return katsayilar, araliklar


def regresyon(gecmis, hedef):
    """Hedefin grubuna ait polinomu hedef sicakliginda hesaplayarak yuk tahmin eder."""
    if egitilmis["katsayilar"] is None:
        katsayilar, araliklar = regresyon_egit(gecmis)
    else:
        katsayilar, araliklar = egitilmis["katsayilar"], egitilmis["araliklar"]

    grup = (hedef["saat"], hedef["hafta_sonu"])
    if grup not in katsayilar:
        # Bu grup icin yeterli veri yoksa haftalik profile donuyoruz
        return haftalik(gecmis, hedef)

    # Egitimde hic gorulmemis bir sicaklik girilirse (orn. gece 05:00'te 35 derece)
    # parabol cok sacma degerler veriyor. O yuzden sicakligi grubun
    # egitimde gordugu araliga sinirliyoruz.
    en_dusuk, en_yuksek = araliklar[grup]
    sicaklik = min(max(hedef["sicaklik"], en_dusuk), en_yuksek)
    return float(np.polyval(katsayilar[grup], sicaklik))


# ---------------------------------------------------------------------------
# 4) Bonus: Random Forest (sklearn)
#    Ozellikler: saat, gun, sicaklik, 24 saat onceki yuk (lag-24)
# ---------------------------------------------------------------------------
OZELLIK_ISIMLERI = ["saat", "gun", "sicaklik", "lag-24"]


def ozellik_cikar(gecmis, hedef):
    """RF icin [saat, gun, sicaklik, lag24] ozellik listesini olusturur."""
    onceki = onceki_kayit(gecmis, hedef, 24)
    if onceki is None:
        return None
    return [hedef["saat"], hedef["gun"], hedef["sicaklik"], onceki["yuk"]]


def rf_egit(gecmis):
    """Gecmis veriden Random Forest modelini egitir."""
    X = []
    y = []
    # Ilk 24 saatin lag-24 degeri olmadigi icin 24'ten basliyoruz
    for i in range(24, len(gecmis)):
        # gecmis[:i] diye kesmek her seferinde liste kopyaladigi icin yavas,
        # onceki_kayit zaten 24 saat oncesini buldugu icin tum listeyi veriyoruz
        ozellikler = ozellik_cikar(gecmis, gecmis[i])
        if ozellikler is not None:
            X.append(ozellikler)
            y.append(gecmis[i]["yuk"])

    if len(X) < 10:
        raise ValueError("Random Forest için yeterli veri yok.")

    model = RandomForestRegressor(n_estimators=60, max_depth=14, random_state=0)
    model.fit(X, y)
    return model


def random_forest(gecmis, hedef):
    """Egitilmis Random Forest ile hedef saatin yukunu tahmin eder."""
    model = egitilmis["rf"]
    if model is None:
        model = rf_egit(gecmis)
        egitilmis["rf"] = model

    ozellikler = ozellik_cikar(gecmis, hedef)
    if ozellikler is None:
        raise ValueError("RF için 24 saat önceki veri yok.")
    return float(model.predict([ozellikler])[0])


def ozellik_onemleri():
    """Egitilmis RF modelinin ozellik onemlerini {isim: onem} olarak dondurur."""
    if egitilmis["rf"] is None:
        return None
    onemler = {}
    for isim, deger in zip(OZELLIK_ISIMLERI, egitilmis["rf"].feature_importances_):
        onemler[isim] = float(deger)
    return onemler


# ---------------------------------------------------------------------------
# Ortak fonksiyonlar
# ---------------------------------------------------------------------------
def hazirla(egitim_verisi, rf_dahil=False):
    """Regresyonu (ve istenirse RF'yi) verilen egitim verisiyle bir kere egitir."""
    egitilmis["veri"] = egitim_verisi
    egitilmis["katsayilar"], egitilmis["araliklar"] = regresyon_egit(egitim_verisi)
    egitilmis["rf"] = None
    if rf_dahil and SKLEARN_VAR:
        egitilmis["rf"] = rf_egit(egitim_verisi)


def model_listesi(rf_dahil=False):
    """Kullanilacak modelleri {isim: fonksiyon} sozlugu olarak dondurur."""
    modeller = {
        "Persistence": persistence,
        "Haftalık profil": haftalik,
        "Regresyon": regresyon,
    }
    if rf_dahil and SKLEARN_VAR:
        modeller["Random Forest"] = random_forest
    return modeller


MODELLER = model_listesi()
