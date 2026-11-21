# plots.py
# Butun grafikler. Kural: her fonksiyon bir matplotlib Figure dondurur,
# plt.show() cagirmaz. Boylece ayni grafik hem Tkinter'a gomulebiliyor
# hem de deneme.py'de PNG olarak kaydedilebiliyor.

from matplotlib.figure import Figure

# Modeller icin sabit renkler, her grafikte ayni model ayni renkte gorunsun
MODEL_RENKLERI = {
    "Persistence": "#9aa5b1",
    "Haftalık profil": "#f0a202",
    "Regresyon": "#d64545",
    "Random Forest": "#2f9e44",
}
GERCEK_RENK = "#1f5fa8"
GUN_ISIMLERI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def yeni_figur(genislik=8, yukseklik=4.6):
    """Ortak ayarlarla bos bir Figure ve tek eksen olusturur."""
    figur = Figure(figsize=(genislik, yukseklik), dpi=100)
    eksen = figur.add_subplot(111)
    eksen.grid(True, alpha=0.3)
    eksen.spines["top"].set_visible(False)
    eksen.spines["right"].set_visible(False)
    return figur, eksen


def gercek_vs_tahmin(test, tahminler, saat_sayisi=168, secili_model=None):
    """Test doneminin son saat_sayisi saati icin gercek ve tahmin egrilerini cizer."""
    figur, eksen = yeni_figur()
    parca = test[-saat_sayisi:]
    tarihler = [k["tarih"] for k in parca]
    gercekler = [k["yuk"] for k in parca]

    # zorder buyuk olunca gercek egri tahminlerin ustunde ciziliyor
    eksen.plot(tarihler, gercekler, color=GERCEK_RENK, linewidth=2.2, label="Gerçek",
               zorder=5)

    for isim, liste in tahminler.items():
        if secili_model is not None and isim != secili_model:
            continue
        renk = MODEL_RENKLERI.get(isim, "black")
        eksen.plot(tarihler, liste[-saat_sayisi:], color=renk, linestyle="--",
                   linewidth=1.4, label=isim)

    eksen.set_title(f"Gerçek ve tahmin edilen yük (son {saat_sayisi} saat)")
    eksen.set_ylabel("Yük (MW)")
    eksen.legend(loc="upper left", fontsize=8)
    figur.autofmt_xdate()
    figur.tight_layout()
    return figur


def sicaklik_yuk(veri):
    """Sicaklik-yuk sacilim grafigini cizer (U egrisi)."""
    figur, eksen = yeni_figur()
    sicakliklar = [k["sicaklik"] for k in veri]
    yukler = [k["yuk"] for k in veri]
    renkler = [k["saat"] for k in veri]

    nokta = eksen.scatter(sicakliklar, yukler, c=renkler, cmap="viridis", s=5, alpha=0.5)
    cubuk = figur.colorbar(nokta, ax=eksen)
    cubuk.set_label("Saat")

    # 18-22 derece arasi konfor bolgesi
    eksen.axvspan(18, 22, color="green", alpha=0.08, label="Konfor bölgesi (18-22 °C)")
    eksen.set_title("Sıcaklık - Yük ilişkisi")
    eksen.set_xlabel("Sıcaklık (°C)")
    eksen.set_ylabel("Yük (MW)")
    eksen.legend(loc="upper center", fontsize=8)
    figur.tight_layout()
    return figur


def gunluk_profil(veri):
    """Saat basina ortalama yuku hafta ici ve hafta sonu icin ayri cizer."""
    figur, eksen = yeni_figur()

    # toplamlar[hafta_sonu][saat] seklinde toplam ve sayi tutuyoruz
    toplamlar = {False: [0.0] * 24, True: [0.0] * 24}
    sayilar = {False: [0] * 24, True: [0] * 24}
    for kayit in veri:
        toplamlar[kayit["hafta_sonu"]][kayit["saat"]] += kayit["yuk"]
        sayilar[kayit["hafta_sonu"]][kayit["saat"]] += 1

    saatler = list(range(24))
    etiketler = {False: "Hafta içi", True: "Hafta sonu"}
    renkler = {False: GERCEK_RENK, True: "#f0a202"}
    for hafta_sonu in [False, True]:
        ortalamalar = []
        for s in saatler:
            if sayilar[hafta_sonu][s] > 0:
                ortalamalar.append(toplamlar[hafta_sonu][s] / sayilar[hafta_sonu][s])
            else:
                ortalamalar.append(None)
        eksen.plot(saatler, ortalamalar, marker="o", markersize=4,
                   color=renkler[hafta_sonu], label=etiketler[hafta_sonu])

    eksen.set_xticks(range(0, 24, 2))
    eksen.set_title("Günlük yük profili (saat başına ortalama)")
    eksen.set_xlabel("Saat")
    eksen.set_ylabel("Ortalama yük (MW)")
    eksen.legend(fontsize=9)
    figur.tight_layout()
    return figur


def gun_bazinda_ortalama(veri):
    """Haftanin her gunu icin ortalama yuku cubuk grafikle gosterir."""
    figur, eksen = yeni_figur()
    toplam = [0.0] * 7
    sayi = [0] * 7
    for kayit in veri:
        toplam[kayit["gun"]] += kayit["yuk"]
        sayi[kayit["gun"]] += 1

    ortalamalar = []
    for i in range(7):
        ortalamalar.append(toplam[i] / sayi[i] if sayi[i] > 0 else 0)

    renkler = [GERCEK_RENK] * 5 + ["#f0a202"] * 2
    cubuklar = eksen.bar(GUN_ISIMLERI, ortalamalar, color=renkler)
    for cubuk, deger in zip(cubuklar, ortalamalar):
        eksen.text(cubuk.get_x() + cubuk.get_width() / 2, deger, f"{deger:,.0f}",
                   ha="center", va="bottom", fontsize=8)

    # Farklar gorunsun diye y eksenini sifirdan baslatmiyoruz
    dolu = [o for o in ortalamalar if o > 0]
    if dolu:
        eksen.set_ylim(min(dolu) * 0.9, max(dolu) * 1.05)
    eksen.set_title("Haftanın günlerine göre ortalama yük")
    eksen.set_ylabel("Ortalama yük (MW)")
    figur.tight_layout()
    return figur


def yillik_seyir(veri):
    """Gunluk ortalama yuk ve sicakligi zaman icinde iki eksenli cizer."""
    figur, eksen = yeni_figur()

    # Saatlik veriyi gunluk ortalamaya ceviriyoruz
    gunluk = {}
    for kayit in veri:
        gun = kayit["tarih"].date()
        if gun not in gunluk:
            gunluk[gun] = {"yuk": 0.0, "sicaklik": 0.0, "n": 0}
        gunluk[gun]["yuk"] += kayit["yuk"]
        gunluk[gun]["sicaklik"] += kayit["sicaklik"]
        gunluk[gun]["n"] += 1

    gunler = sorted(gunluk.keys())
    yukler = [gunluk[g]["yuk"] / gunluk[g]["n"] for g in gunler]
    sicakliklar = [gunluk[g]["sicaklik"] / gunluk[g]["n"] for g in gunler]

    eksen.plot(gunler, yukler, color=GERCEK_RENK, linewidth=1.2, label="Günlük ort. yük")
    eksen.set_ylabel("Yük (MW)", color=GERCEK_RENK)

    eksen2 = eksen.twinx()
    eksen2.plot(gunler, sicakliklar, color="#d64545", linewidth=1, alpha=0.7)
    eksen2.set_ylabel("Sıcaklık (°C)", color="#d64545")
    eksen2.spines["top"].set_visible(False)

    eksen.set_title("Günlük ortalama yük ve sıcaklık")
    figur.autofmt_xdate()
    figur.tight_layout()
    return figur


def model_karsilastirma(sonuclar, metrik="MAPE"):
    """Her modelin secilen metrigini cubuk grafikle karsilastirir."""
    figur, eksen = yeni_figur()
    isimler = list(sonuclar.keys())
    degerler = [sonuclar[i][metrik] for i in isimler]
    renkler = [MODEL_RENKLERI.get(i, "gray") for i in isimler]

    cubuklar = eksen.bar(isimler, degerler, color=renkler, width=0.55)
    for cubuk, deger in zip(cubuklar, degerler):
        if metrik == "MAPE":
            yazi = f"%{deger:.2f}"
        else:
            yazi = f"{deger:,.0f}"
        eksen.text(cubuk.get_x() + cubuk.get_width() / 2, deger, yazi,
                   ha="center", va="bottom", fontsize=9, fontweight="bold")

    birim = "(%)" if metrik == "MAPE" else "(MW)"
    eksen.set_title(f"Modellerin {metrik} karşılaştırması (düşük olan daha iyi)")
    eksen.set_ylabel(f"{metrik} {birim}")
    eksen.set_ylim(0, max(degerler) * 1.18)
    figur.tight_layout()
    return figur


def ozellik_onemi(onemler):
    """Random Forest'in ozellik onemlerini yatay cubuk grafikle gosterir."""
    figur, eksen = yeni_figur()
    # Kucukten buyuge siralayalim ki en onemli en ustte olsun
    sirali = sorted(onemler.items(), key=lambda x: x[1])
    isimler = [s[0] for s in sirali]
    degerler = [s[1] for s in sirali]

    eksen.barh(isimler, degerler, color=MODEL_RENKLERI["Random Forest"])
    for i, deger in enumerate(degerler):
        eksen.text(deger, i, f" {deger:.2f}", va="center", fontsize=9)
    eksen.set_xlim(0, max(degerler) * 1.15)
    eksen.set_title("Random Forest - özellik önemleri")
    eksen.set_xlabel("Önem")
    figur.tight_layout()
    return figur


def tahmin_grafigi(veri, hedef, tahminler):
    """Son 48 saatin gercek yukunu ve hedef saat icin model tahminlerini cizer."""
    figur, eksen = yeni_figur(7, 4)
    son = veri[-48:]
    eksen.plot([k["tarih"] for k in son], [k["yuk"] for k in son],
               color=GERCEK_RENK, linewidth=2, label="Son 48 saat (gerçek)")

    for isim, deger in tahminler.items():
        eksen.scatter([hedef["tarih"]], [deger], s=70, zorder=3,
                      color=MODEL_RENKLERI.get(isim, "black"), label=isim,
                      edgecolors="white")

    eksen.axvline(veri[-1]["tarih"], color="gray", linestyle=":", linewidth=1)
    eksen.set_title("Son 48 saat ve seçilen saat için tahminler")
    eksen.set_ylabel("Yük (MW)")
    eksen.legend(fontsize=8, loc="upper left")
    figur.autofmt_xdate()
    figur.tight_layout()
    return figur
