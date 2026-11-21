# main.py
# EEE303 Elektrik Yuk Tahmin Araci - Tkinter arayuzu
# 4 sekme var: Veri, Kesif, Tahmin, Karsilastirma.
# Her sekme ayri bir fonksiyonla kuruluyor (veri_sekmesi_kur gibi).
# Calistirmak icin:  python main.py

import csv
import tkinter as tk
from datetime import timedelta
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import data
import metrics
import models
import plots
import utils

# ---------------------------------------------------------------------------
# Uygulamanin durumu tek yerde tutuluyor
# ---------------------------------------------------------------------------
durum = {
    "veri": None,        # list[dict], yuklu veri
    "kaynak": "",        # "Sentetik" veya dosya adi
    "atlanan": 0,        # CSV'de atlanan bozuk satir sayisi
    "sonuclar": None,    # karsilastirma sonuclari {model: {MAPE, MAE, RMSE}}
    "tahminler": None,   # karsilastirmada her modelin tahmin listesi
    "test": None,        # karsilastirmadaki test verisi
    "onemler": None,     # RF ozellik onemleri
    "figurler": {},      # PNG kaydetmek icin ekrandaki son grafikler
}

# Birden fazla fonksiyonun eristigi widget'lar burada
w = {}

# Renkler
RENK_BASLIK = "#1f3b5c"
RENK_ARKA = "#eef1f5"
RENK_KART = "#ffffff"
RENK_VURGU = "#2b6cb0"
RENK_YAZI = "#1a202c"
RENK_SOLUK = "#5a6474"
RENK_HATA = "#c53030"
RENK_BASARI = "#2f855a"

YAZI = "Helvetica"
TABLO_SATIR_SINIRI = 1000  # Treeview cok yavaslamasin diye en fazla bu kadar satir

KESIF_GRAFIKLERI = {
    "Günlük profil": (plots.gunluk_profil,
                      "Saat başına ortalama yük. Gece 04:00 civarı en düşük, akşam 20:00 "
                      "civarı puant. Hafta sonu yük her saatte hafta içinden düşük."),
    "Sıcaklık - yük": (plots.sicaklik_yuk,
                       "18-22 °C arası konfor bölgesinde yük en düşük. Soğukta ısıtma, "
                       "sıcakta klima yükü artırıyor, bu yüzden U şeklinde bir eğri çıkıyor."),
    "Gün bazında": (plots.gun_bazinda_ortalama,
                    "Haftanın her günü için ortalama yük. Cumartesi ve pazar belirgin "
                    "şekilde düşük, bu yüzden modellerde hafta sonu ayrı ele alınıyor."),
    "Yıllık seyir": (plots.yillik_seyir,
                     "Günlük ortalama yük (mavi) ve sıcaklık (kırmızı). Kışın ve yazın yük "
                     "yükseliyor, ilkbahar ve sonbaharda düşüyor."),
}


# ---------------------------------------------------------------------------
# Genel yardimci fonksiyonlar
# ---------------------------------------------------------------------------
def stil_ayarla(pencere):
    """ttk widget'lari icin renk ve yazi tipi ayarlarini yapar."""
    stil = ttk.Style(pencere)
    stil.theme_use("clam")

    stil.configure(".", background=RENK_ARKA, foreground=RENK_YAZI, font=(YAZI, 12))
    stil.configure("TFrame", background=RENK_ARKA)
    stil.configure("Kart.TFrame", background=RENK_KART)
    stil.configure("TLabel", background=RENK_ARKA)
    stil.configure("Kart.TLabel", background=RENK_KART)
    stil.configure("Soluk.TLabel", background=RENK_KART, foreground=RENK_SOLUK, font=(YAZI, 11))
    stil.configure("Buyuk.TLabel", background=RENK_KART, font=(YAZI, 14, "bold"))
    stil.configure("TLabelframe", background=RENK_KART, bordercolor="#d5dbe3", relief="solid")
    stil.configure("TLabelframe.Label", background=RENK_KART, foreground=RENK_BASLIK,
                   font=(YAZI, 12, "bold"))
    stil.configure("TCheckbutton", background=RENK_KART)
    stil.configure("TRadiobutton", background=RENK_ARKA)

    # Sekmeler
    stil.configure("TNotebook", background=RENK_ARKA, borderwidth=0)
    stil.configure("TNotebook.Tab", padding=(18, 8), font=(YAZI, 12, "bold"),
                   background="#d9dee6", foreground=RENK_SOLUK)
    stil.map("TNotebook.Tab",
             background=[("selected", RENK_KART)],
             foreground=[("selected", RENK_BASLIK)])

    # Butonlar
    stil.configure("TButton", padding=(10, 6), background="#e2e8f0")
    stil.configure("Ana.TButton", padding=(12, 7), font=(YAZI, 12, "bold"),
                   background=RENK_VURGU, foreground="white")
    stil.map("Ana.TButton",
             background=[("disabled", "#a0aec0"), ("active", "#2c5282")],
             foreground=[("disabled", "#edf2f7")])

    # Tablolar
    stil.configure("Treeview", rowheight=24, font=(YAZI, 11), background=RENK_KART,
                   fieldbackground=RENK_KART)
    stil.configure("Treeview.Heading", font=(YAZI, 11, "bold"), background="#dfe5ee",
                   foreground=RENK_BASLIK)
    stil.map("Treeview", background=[("selected", "#bee3f8")],
             foreground=[("selected", RENK_YAZI)])


def veri_var_mi():
    """Veri yuklenmemisse uyari gosterip False dondurur."""
    if durum["veri"] is None:
        messagebox.showwarning("Veri yok",
                               "Önce 'Veri' sekmesinden sentetik veri üretin veya CSV yükleyin.")
        return False
    return True


def durum_yaz(metin, renk=RENK_YAZI):
    """Pencerenin altindaki durum cubuguna mesaj yazar."""
    w["durum"].config(text=metin, fg=renk)


def mesgul(acik):
    """Uzun islemlerde imleci bekleme imlecine cevirir."""
    w["pencere"].config(cursor="watch" if acik else "")
    w["pencere"].update()


def tablo_temizle(tablo):
    """Treeview'deki butun satirlari siler."""
    for satir in tablo.get_children():
        tablo.delete(satir)


def tablo_olustur(ust, sutunlar, genislikler, yukseklik=10):
    """Kaydirma cubuklu bir Treeview olusturup dondurur."""
    cerceve = ttk.Frame(ust, style="Kart.TFrame")
    tablo = ttk.Treeview(cerceve, columns=sutunlar, show="headings", height=yukseklik)
    for sutun, genislik in zip(sutunlar, genislikler):
        tablo.heading(sutun, text=sutun)
        tablo.column(sutun, width=genislik, anchor="center")
    kaydirma = ttk.Scrollbar(cerceve, orient="vertical", command=tablo.yview)
    tablo.configure(yscrollcommand=kaydirma.set)
    tablo.pack(side="left", fill="both", expand=True)
    kaydirma.pack(side="right", fill="y")
    # Satirlari sirayla renklendirmek icin
    tablo.tag_configure("tek", background="#f7f9fc")
    tablo.tag_configure("enIyi", background="#e6f4ea", font=(YAZI, 11, "bold"))
    return cerceve, tablo


def bos_mesaj(cerceve, metin):
    """Grafik alanina, grafik yokken gosterilecek bir bilgi yazisi koyar."""
    for eski in cerceve.winfo_children():
        eski.destroy()
    ttk.Label(cerceve, text=metin, style="Soluk.TLabel", anchor="center",
              justify="center").pack(expand=True)


def grafik_goster(cerceve, figur, anahtar):
    """Matplotlib figurunu verilen cerceveye FigureCanvasTkAgg ile gomer."""
    for eski in cerceve.winfo_children():
        eski.destroy()
    tuval = FigureCanvasTkAgg(figur, master=cerceve)
    tuval.draw()
    arac_cubugu = NavigationToolbar2Tk(tuval, cerceve, pack_toolbar=False)
    arac_cubugu.update()
    arac_cubugu.pack(side="bottom", fill="x")
    tuval.get_tk_widget().pack(fill="both", expand=True)
    durum["figurler"][anahtar] = figur


def kart(ust, baslik):
    """Basligi olan beyaz bir LabelFrame (kart) olusturur."""
    return ttk.LabelFrame(ust, text=" " + baslik + " ", padding=12)


# ---------------------------------------------------------------------------
# 1) VERI SEKMESI
# ---------------------------------------------------------------------------
def veri_sekmesi_kur(defter):
    """Veri sekmesini kurar: sentetik uretim, CSV yukleme, rapor ve tablo."""
    sekme = ttk.Frame(defter, padding=14)
    defter.add(sekme, text="  1. Veri  ")

    sol = ttk.Frame(sekme)
    sol.pack(side="left", fill="y", padx=(0, 14))
    sag = ttk.Frame(sekme)
    sag.pack(side="left", fill="both", expand=True)

    # --- Sentetik veri karti
    k1 = kart(sol, "Sentetik veri üret")
    k1.pack(fill="x", pady=(0, 10))
    ttk.Label(k1, text="Gün sayısı (35 - 730):", style="Kart.TLabel").pack(anchor="w")
    w["gun_sayisi"] = ttk.Entry(k1, width=12)
    w["gun_sayisi"].insert(0, "365")
    w["gun_sayisi"].pack(anchor="w", pady=(2, 8))
    ttk.Button(k1, text="Sentetik Veri Üret", style="Ana.TButton",
               command=sentetik_tiklandi).pack(fill="x")

    # --- CSV karti
    k2 = kart(sol, "Dosyadan yükle")
    k2.pack(fill="x", pady=(0, 10))
    ttk.Button(k2, text="CSV Dosyası Seç...", command=csv_tiklandi).pack(fill="x")
    ttk.Label(k2, text="Gerekli sütunlar: tarih, sicaklik, yuk\nTarih: YYYY-AA-GG SS:DD",
              style="Soluk.TLabel").pack(anchor="w", pady=(6, 0))

    # --- Kaydetme karti
    k3 = kart(sol, "Dışa aktar")
    k3.pack(fill="x", pady=(0, 10))
    ttk.Button(k3, text="Veriyi CSV Olarak Kaydet", command=veri_kaydet_tiklandi).pack(fill="x")

    # --- Rapor karti
    k4 = kart(sol, "Veri raporu")
    k4.pack(fill="both", expand=True)
    w["rapor"] = tk.Label(k4, text="Henüz veri yüklenmedi.", justify="left", anchor="nw",
                          bg=RENK_KART, fg=RENK_SOLUK, font=("Menlo", 11))
    w["rapor"].pack(fill="both", expand=True)

    # --- Sag taraf: veri tablosu
    k5 = kart(sag, "Veri tablosu")
    k5.pack(fill="both", expand=True)
    sutunlar = ("Tarih", "Saat", "Gün", "Hafta sonu", "Sıcaklık (°C)", "Yük (MW)")
    cerceve, w["veri_tablosu"] = tablo_olustur(k5, sutunlar, [150, 60, 60, 90, 110, 120], 20)
    cerceve.pack(fill="both", expand=True)
    w["tablo_bilgi"] = ttk.Label(k5, text="", style="Soluk.TLabel")
    w["tablo_bilgi"].pack(anchor="w", pady=(6, 0))


def sentetik_tiklandi():
    """Sentetik veri uret butonuna basilinca calisir."""
    gun, hata = utils.tam_sayi_al(w["gun_sayisi"].get(), 35, 730)
    if hata:
        messagebox.showerror("Hatalı giriş", "Gün sayısı: " + hata)
        return
    mesgul(True)
    veri = data.sentetik_uret(gun)
    mesgul(False)
    veri_yukle(veri, "Sentetik", 0)


def csv_tiklandi():
    """CSV dosyasi sec butonuna basilinca dosyayi okuyup yukler."""
    yol = filedialog.askopenfilename(
        title="Yük verisi CSV dosyasını seçin",
        initialdir="data",
        filetypes=[("CSV dosyaları", "*.csv"), ("Tüm dosyalar", "*.*")],
    )
    if not yol:
        return  # kullanici vazgecti

    yol, hata = utils.dosya_kontrol(yol)
    if hata:
        messagebox.showerror("Dosya hatası", hata)
        return

    try:
        veri, atlanan = data.csv_oku(yol)
    except (FileNotFoundError, ValueError) as e:
        messagebox.showerror("CSV okunamadı", str(e))
        return
    except UnicodeDecodeError:
        messagebox.showerror("CSV okunamadı", "Dosya metin (UTF-8) formatında değil.")
        return

    if len(veri) < 48:
        messagebox.showerror("Veri yetersiz",
                             f"Dosyada sadece {len(veri)} geçerli satır var. "
                             "Tahmin yapabilmek için en az 48 saatlik (2 gün) veri gerekli.")
        return

    dosya_adi = yol.replace("\\", "/").split("/")[-1]
    veri_yukle(veri, dosya_adi, atlanan)
    if atlanan > 0:
        messagebox.showinfo("Bozuk satırlar",
                            f"{atlanan} satır boş, eksik veya hatalı olduğu için atlandı.")


def veri_kaydet_tiklandi():
    """Yuklu veriyi kullanicinin sectigi CSV dosyasina kaydeder."""
    if not veri_var_mi():
        return
    yol = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="yuk_verisi.csv",
                                       filetypes=[("CSV dosyaları", "*.csv")])
    if not yol:
        return
    try:
        data.csv_kaydet(durum["veri"], yol)
    except OSError as e:
        messagebox.showerror("Kaydedilemedi", str(e))
        return
    durum_yaz("Veri kaydedildi: " + yol, RENK_BASARI)


def veri_yukle(veri, kaynak, atlanan):
    """Yeni veriyi duruma koyar ve butun sekmeleri gunceller."""
    durum["veri"] = veri
    durum["kaynak"] = kaynak
    durum["atlanan"] = atlanan
    # Eski karsilastirma sonuclari yeni veriye ait degil, siliyoruz
    durum["sonuclar"] = None
    durum["tahminler"] = None
    durum["test"] = None
    durum["onemler"] = None
    durum["figurler"] = {}
    models.egitilmis["veri"] = None

    rapor_guncelle()
    veri_tablosu_guncelle()
    kesif_ciz()
    tahmin_sekmesi_sifirla()
    karsilastirma_sifirla()

    ozet = data.veri_ozeti(veri)
    durum_yaz(f"{kaynak}: {ozet['kayit']} kayıt yüklendi "
              f"({utils.tarih_yaz(ozet['baslangic'])} - {utils.tarih_yaz(ozet['bitis'])})",
              RENK_BASARI)


def rapor_guncelle():
    """Veri raporu kartindaki ozet bilgileri yazar."""
    ozet = data.veri_ozeti(durum["veri"])
    satirlar = [
        f"Kaynak     : {durum['kaynak']}",
        f"Kayıt      : {ozet['kayit']} saat ({ozet['gun']:.0f} gün)",
        f"Başlangıç  : {utils.tarih_yaz(ozet['baslangic'])}",
        f"Bitiş      : {utils.tarih_yaz(ozet['bitis'])}",
        f"Atlanan    : {durum['atlanan']} satır",
        f"Eksik saat : {ozet['eksik_saat']}",
        "",
        f"Yük  min   : {utils.mw_yaz(ozet['yuk_min'])}",
        f"Yük  max   : {utils.mw_yaz(ozet['yuk_max'])}",
        f"Yük  ort   : {utils.mw_yaz(ozet['yuk_ort'])}",
        f"Sıcaklık   : {ozet['sic_min']:.1f} / {ozet['sic_max']:.1f} °C",
    ]
    w["rapor"].config(text="\n".join(satirlar), fg=RENK_YAZI)


def veri_tablosu_guncelle():
    """Veri tablosunu yuklu verinin ilk kayitlariyla doldurur."""
    tablo = w["veri_tablosu"]
    tablo_temizle(tablo)
    veri = durum["veri"]
    for i, kayit in enumerate(veri[:TABLO_SATIR_SINIRI]):
        etiket = "tek" if i % 2 else ""
        tablo.insert("", "end", tags=(etiket,), values=(
            kayit["tarih"].strftime("%d.%m.%Y"),
            f"{kayit['saat']:02d}:00",
            plots.GUN_ISIMLERI[kayit["gun"]],
            "Evet" if kayit["hafta_sonu"] else "Hayır",
            f"{kayit['sicaklik']:.1f}",
            f"{kayit['yuk']:,.0f}".replace(",", "."),
        ))
    if len(veri) > TABLO_SATIR_SINIRI:
        w["tablo_bilgi"].config(text=f"Toplam {len(veri)} kayıttan ilk {TABLO_SATIR_SINIRI} "
                                     "tanesi gösteriliyor.")
    else:
        w["tablo_bilgi"].config(text=f"Toplam {len(veri)} kayıt.")


# ---------------------------------------------------------------------------
# 2) KESIF SEKMESI
# ---------------------------------------------------------------------------
def kesif_sekmesi_kur(defter):
    """Kesif sekmesini kurar: grafik secimi ve grafik alani."""
    sekme = ttk.Frame(defter, padding=14)
    defter.add(sekme, text="  2. Keşif  ")

    ust = ttk.Frame(sekme)
    ust.pack(fill="x", pady=(0, 8))
    ttk.Label(ust, text="Grafik:", font=(YAZI, 12, "bold")).pack(side="left", padx=(0, 8))
    w["kesif_secim"] = tk.StringVar(value="Günlük profil")
    for isim in KESIF_GRAFIKLERI:
        ttk.Radiobutton(ust, text=isim, value=isim, variable=w["kesif_secim"],
                        command=kesif_ciz).pack(side="left", padx=6)

    k = kart(sekme, "Grafik")
    k.pack(fill="both", expand=True)
    w["kesif_aciklama"] = ttk.Label(k, text="", style="Soluk.TLabel", wraplength=900)
    w["kesif_aciklama"].pack(anchor="w", pady=(0, 6))
    w["kesif_alan"] = ttk.Frame(k, style="Kart.TFrame")
    w["kesif_alan"].pack(fill="both", expand=True)
    bos_mesaj(w["kesif_alan"], "Grafikleri görmek için önce 'Veri' sekmesinden veri yükleyin.")


def kesif_ciz():
    """Secili kesif grafigini cizer."""
    if durum["veri"] is None:
        return
    secim = w["kesif_secim"].get()
    fonksiyon, aciklama = KESIF_GRAFIKLERI[secim]
    w["kesif_aciklama"].config(text=aciklama)
    figur = fonksiyon(durum["veri"])
    grafik_goster(w["kesif_alan"], figur, "kesif")


# ---------------------------------------------------------------------------
# 3) TAHMIN SEKMESI
# ---------------------------------------------------------------------------
def tahmin_sekmesi_kur(defter):
    """Tahmin sekmesini kurar: tarih, saat, sicaklik girisleri ve sonuclar."""
    sekme = ttk.Frame(defter, padding=14)
    defter.add(sekme, text="  3. Tahmin  ")

    sol = ttk.Frame(sekme)
    sol.pack(side="left", fill="y", padx=(0, 14))
    sag = ttk.Frame(sekme)
    sag.pack(side="left", fill="both", expand=True)

    k1 = kart(sol, "Tahmin girdileri")
    k1.pack(fill="x")
    w["tahmin_aralik"] = ttk.Label(k1, text="Önce veri yükleyin.", style="Soluk.TLabel",
                                   wraplength=250, justify="left")
    w["tahmin_aralik"].pack(anchor="w", pady=(0, 10))

    ttk.Label(k1, text="Tarih (GG.AA.YYYY):", style="Kart.TLabel").pack(anchor="w")
    w["tahmin_tarih"] = ttk.Entry(k1, width=16)
    w["tahmin_tarih"].pack(anchor="w", pady=(2, 8))

    ttk.Label(k1, text="Saat (0 - 23):", style="Kart.TLabel").pack(anchor="w")
    w["tahmin_saat"] = ttk.Spinbox(k1, from_=0, to=23, width=6)
    w["tahmin_saat"].set("18")
    w["tahmin_saat"].pack(anchor="w", pady=(2, 8))

    ttk.Label(k1, text="Sıcaklık (°C, -40 ile 55 arası):", style="Kart.TLabel").pack(anchor="w")
    w["tahmin_sicaklik"] = ttk.Entry(k1, width=10)
    w["tahmin_sicaklik"].insert(0, "20")
    w["tahmin_sicaklik"].pack(anchor="w", pady=(2, 8))

    w["tahmin_rf"] = tk.BooleanVar(value=False)
    rf_kutu = ttk.Checkbutton(k1, text="Random Forest'ı da çalıştır", variable=w["tahmin_rf"])
    rf_kutu.pack(anchor="w", pady=(0, 10))
    if not models.SKLEARN_VAR:
        rf_kutu.config(state="disabled", text="Random Forest (sklearn yüklü değil)")

    ttk.Button(k1, text="Tahmin Et", style="Ana.TButton",
               command=tahmin_tiklandi).pack(fill="x")
    w["tahmin_bilgi"] = ttk.Label(k1, text="", style="Soluk.TLabel")
    w["tahmin_bilgi"].pack(anchor="w", pady=(8, 0))

    # --- Sag taraf: sonuc tablosu ve grafik
    k2 = kart(sag, "Model tahminleri")
    k2.pack(fill="x", pady=(0, 10))
    w["tahmin_baslik"] = ttk.Label(k2, text="", style="Buyuk.TLabel")
    w["tahmin_baslik"].pack(anchor="w", pady=(0, 6))
    sutunlar = ("Model", "Tahmin (MW)", "Dünküne göre fark")
    cerceve, w["tahmin_tablosu"] = tablo_olustur(k2, sutunlar, [200, 160, 180], 4)
    cerceve.pack(fill="x")

    k3 = kart(sag, "Grafik")
    k3.pack(fill="both", expand=True)
    w["tahmin_alan"] = ttk.Frame(k3, style="Kart.TFrame")
    w["tahmin_alan"].pack(fill="both", expand=True)
    bos_mesaj(w["tahmin_alan"], "Tahmin yapıldığında burada son 48 saat ve tahminler görünecek.")


def tahmin_sekmesi_sifirla():
    """Yeni veri yuklenince tahmin sekmesindeki varsayilan degerleri ayarlar."""
    son = durum["veri"][-1]["tarih"]
    ilk_saat = son + timedelta(hours=1)
    son_saat = son + timedelta(hours=24)
    w["tahmin_aralik"].config(
        text="Tahmin, verinin bittiği andan sonraki 24 saat için yapılabilir:\n"
             f"{utils.tarih_yaz(ilk_saat)}  -  {utils.tarih_yaz(son_saat)}")
    w["tahmin_tarih"].delete(0, "end")
    w["tahmin_tarih"].insert(0, ilk_saat.strftime("%d.%m.%Y"))
    # Varsayilan sicaklik olarak son kaydin sicakligini koyuyoruz
    w["tahmin_sicaklik"].delete(0, "end")
    w["tahmin_sicaklik"].insert(0, str(durum["veri"][-1]["sicaklik"]))
    tablo_temizle(w["tahmin_tablosu"])
    w["tahmin_baslik"].config(text="")
    bos_mesaj(w["tahmin_alan"], "Tahmin yapıldığında burada son 48 saat ve tahminler görünecek.")


def tahmin_girdilerini_al():
    """Tahmin formundaki girdileri dogrular; hedef kaydi veya None dondurur."""
    tarih, hata = utils.tarih_al(w["tahmin_tarih"].get())
    if hata:
        messagebox.showerror("Hatalı tarih", hata)
        return None
    saat, hata = utils.tam_sayi_al(w["tahmin_saat"].get(), 0, 23)
    if hata:
        messagebox.showerror("Hatalı saat", "Saat: " + hata)
        return None
    sicaklik, hata = utils.sayi_al(w["tahmin_sicaklik"].get(), -40, 55)
    if hata:
        messagebox.showerror("Hatalı sıcaklık", "Sıcaklık: " + hata)
        return None

    hedef_tarih = tarih + timedelta(hours=saat)
    son = durum["veri"][-1]["tarih"]
    ilk_izin = son + timedelta(hours=1)
    son_izin = son + timedelta(hours=24)
    if not ilk_izin <= hedef_tarih <= son_izin:
        messagebox.showerror(
            "Tarih aralık dışında",
            "Modeller geçmiş veriye (dün ve geçen haftalar) ihtiyaç duyduğu için tahmin "
            "sadece verinin bitiminden sonraki 24 saat için yapılabilir:\n\n"
            f"{utils.tarih_yaz(ilk_izin)} - {utils.tarih_yaz(son_izin)}")
        return None

    # Yuk bilinmedigi icin None, modeller bu alani kullanmiyor
    return data.kayit_olustur(hedef_tarih, sicaklik, None)


def tahmin_tiklandi():
    """Tahmin et butonuna basilinca butun modelleri calistirir."""
    if not veri_var_mi():
        return
    hedef = tahmin_girdilerini_al()
    if hedef is None:
        return

    veri = durum["veri"]
    rf_dahil = w["tahmin_rf"].get()

    # Modeller bu veriyle egitilmemisse (veya RF istenip egitilmemisse) egitiyoruz
    if models.egitilmis["veri"] is not veri or (rf_dahil and models.egitilmis["rf"] is None):
        w["tahmin_bilgi"].config(text="Hesaplanıyor...", foreground=RENK_VURGU)
        mesgul(True)
        try:
            models.hazirla(veri, rf_dahil)
        except ValueError as e:
            mesgul(False)
            w["tahmin_bilgi"].config(text="")
            messagebox.showerror("Model eğitilemedi", str(e))
            return
        mesgul(False)
    w["tahmin_bilgi"].config(text="")

    # Dunku ayni saatin gercek yuku, karsilastirma icin
    dun = models.onceki_kayit(veri, hedef, 24)

    tablo = w["tahmin_tablosu"]
    tablo_temizle(tablo)
    tahminler = {}
    for isim, fonksiyon in models.model_listesi(rf_dahil).items():
        try:
            deger = fonksiyon(veri, hedef)
        except ValueError as e:
            tablo.insert("", "end", values=(isim, "hesaplanamadı", str(e)))
            continue
        tahminler[isim] = deger
        if dun is not None:
            fark = (deger - dun["yuk"]) / dun["yuk"] * 100
            fark_yazi = f"{fark:+.1f} %"
        else:
            fark_yazi = "-"
        tablo.insert("", "end", values=(isim, utils.mw_yaz(deger), fark_yazi))

    gun_adi = plots.GUN_ISIMLERI[hedef["gun"]]
    w["tahmin_baslik"].config(
        text=f"{utils.tarih_yaz(hedef['tarih'])} ({gun_adi})  •  {hedef['sicaklik']:.1f} °C")

    if tahminler:
        grafik_goster(w["tahmin_alan"], plots.tahmin_grafigi(veri, hedef, tahminler), "tahmin")
        durum_yaz(f"{len(tahminler)} model ile tahmin yapıldı.", RENK_BASARI)


# ---------------------------------------------------------------------------
# 4) KARSILASTIRMA SEKMESI
# ---------------------------------------------------------------------------
def karsilastirma_sekmesi_kur(defter):
    """Karsilastirma sekmesini kurar: test ayarlari, metrik tablosu ve grafikler."""
    sekme = ttk.Frame(defter, padding=14)
    defter.add(sekme, text="  4. Karşılaştırma  ")

    sol = ttk.Frame(sekme)
    sol.pack(side="left", fill="y", padx=(0, 14))
    sag = ttk.Frame(sekme)
    sag.pack(side="left", fill="both", expand=True)

    # --- Ayarlar
    k1 = kart(sol, "Test ayarları")
    k1.pack(fill="x", pady=(0, 10))
    ttk.Label(k1, text="Test için son kaç gün (1 - 90):", style="Kart.TLabel").pack(anchor="w")
    w["test_gun"] = ttk.Entry(k1, width=10)
    w["test_gun"].insert(0, "30")
    w["test_gun"].pack(anchor="w", pady=(2, 8))

    w["karsilastir_rf"] = tk.BooleanVar(value=models.SKLEARN_VAR)
    rf_kutu = ttk.Checkbutton(k1, text="Random Forest (bonus)", variable=w["karsilastir_rf"])
    rf_kutu.pack(anchor="w", pady=(0, 10))
    if not models.SKLEARN_VAR:
        rf_kutu.config(state="disabled", text="Random Forest (sklearn yüklü değil)")

    ttk.Button(k1, text="Karşılaştırmayı Çalıştır", style="Ana.TButton",
               command=karsilastir_tiklandi).pack(fill="x")
    w["karsilastir_bilgi"] = ttk.Label(k1, text="", style="Soluk.TLabel", wraplength=260)
    w["karsilastir_bilgi"].pack(anchor="w", pady=(8, 0))

    # --- Sonuc tablosu
    k2 = kart(sol, "Sonuçlar")
    k2.pack(fill="x", pady=(0, 10))
    sutunlar = ("Model", "MAPE (%)", "MAE (MW)", "RMSE (MW)")
    cerceve, w["sonuc_tablosu"] = tablo_olustur(k2, sutunlar, [120, 70, 80, 85], 4)
    cerceve.pack(fill="x")
    w["en_iyi"] = ttk.Label(k2, text="", style="Kart.TLabel", font=(YAZI, 12, "bold"),
                            foreground=RENK_BASARI, wraplength=340)
    w["en_iyi"].pack(anchor="w", pady=(8, 0))

    # --- Disa aktarma
    k3 = kart(sol, "Dışa aktar")
    k3.pack(fill="x")
    ttk.Button(k3, text="Sonuçları CSV Kaydet", command=sonuc_kaydet_tiklandi).pack(fill="x")
    ttk.Button(k3, text="Grafiği PNG Kaydet", command=png_kaydet_tiklandi).pack(fill="x",
                                                                                 pady=(6, 0))

    # --- Grafik alani
    ust = ttk.Frame(sag)
    ust.pack(fill="x", pady=(0, 8))
    ttk.Label(ust, text="Grafik:", font=(YAZI, 12, "bold")).pack(side="left", padx=(0, 8))
    w["karsilastir_secim"] = tk.StringVar(value="Gerçek vs tahmin")
    for isim in ["Gerçek vs tahmin", "MAPE", "MAE", "Özellik önemi (RF)"]:
        ttk.Radiobutton(ust, text=isim, value=isim, variable=w["karsilastir_secim"],
                        command=karsilastirma_ciz).pack(side="left", padx=6)

    ttk.Label(ust, text="Model:").pack(side="left", padx=(16, 4))
    w["model_secim"] = ttk.Combobox(ust, state="readonly", width=16, values=["Tümü"])
    w["model_secim"].set("Tümü")
    w["model_secim"].pack(side="left")
    w["model_secim"].bind("<<ComboboxSelected>>", lambda olay: karsilastirma_ciz())

    k4 = kart(sag, "Grafik")
    k4.pack(fill="both", expand=True)
    w["karsilastir_alan"] = ttk.Frame(k4, style="Kart.TFrame")
    w["karsilastir_alan"].pack(fill="both", expand=True)
    bos_mesaj(w["karsilastir_alan"], "Sonuçları görmek için 'Karşılaştırmayı Çalıştır'a basın.")


def karsilastirma_sifirla():
    """Yeni veri yuklenince eski karsilastirma sonuclarini temizler."""
    tablo_temizle(w["sonuc_tablosu"])
    w["en_iyi"].config(text="")
    w["karsilastir_bilgi"].config(text="")
    w["model_secim"].config(values=["Tümü"])
    w["model_secim"].set("Tümü")
    bos_mesaj(w["karsilastir_alan"], "Sonuçları görmek için 'Karşılaştırmayı Çalıştır'a basın.")


def karsilastir_tiklandi():
    """Karsilastirma butonuna basilinca modelleri test doneminde degerlendirir."""
    if not veri_var_mi():
        return
    test_gun, hata = utils.tam_sayi_al(w["test_gun"].get(), 1, 90)
    if hata:
        messagebox.showerror("Hatalı giriş", "Test gün sayısı: " + hata)
        return

    rf_dahil = w["karsilastir_rf"].get()
    w["karsilastir_bilgi"].config(text="Hesaplanıyor... (RF seçiliyse birkaç saniye sürebilir)",
                                  foreground=RENK_VURGU)
    mesgul(True)
    try:
        sonuclar, tahminler, test = metrics.karsilastir(durum["veri"], test_gun, rf_dahil)
    except ValueError as e:
        mesgul(False)
        w["karsilastir_bilgi"].config(text="")
        messagebox.showerror("Karşılaştırma yapılamadı", str(e))
        return
    mesgul(False)

    durum["sonuclar"] = sonuclar
    durum["tahminler"] = tahminler
    durum["test"] = test
    durum["onemler"] = models.ozellik_onemleri() if rf_dahil else None
    # Karsilastirmada modeller sadece egitim kismiyla egitildi,
    # tahmin sekmesi tum veriyle tekrar egitsin diye isaretliyoruz
    models.egitilmis["veri"] = None

    # Tabloyu doldur
    en_iyi = metrics.en_iyi_model(sonuclar)
    tablo = w["sonuc_tablosu"]
    tablo_temizle(tablo)
    for isim, m in sonuclar.items():
        etiket = "enIyi" if isim == en_iyi else ""
        tablo.insert("", "end", tags=(etiket,), values=(
            isim, f"{m['MAPE']:.2f}", f"{m['MAE']:,.0f}".replace(",", "."),
            f"{m['RMSE']:,.0f}".replace(",", ".")))

    w["en_iyi"].config(text=f"En iyi model: {en_iyi}  (MAPE %{sonuclar[en_iyi]['MAPE']:.2f})")
    w["karsilastir_bilgi"].config(
        text=f"Eğitim: {len(durum['veri']) - len(test)} saat, test: {len(test)} saat",
        foreground=RENK_SOLUK)
    w["model_secim"].config(values=["Tümü"] + list(sonuclar.keys()))
    karsilastirma_ciz()
    durum_yaz(f"Karşılaştırma tamamlandı. En iyi model: {en_iyi}", RENK_BASARI)


def karsilastirma_ciz():
    """Karsilastirma sekmesinde secili grafigi cizer."""
    if durum["sonuclar"] is None:
        return
    secim = w["karsilastir_secim"].get()

    if secim == "Gerçek vs tahmin":
        model = w["model_secim"].get()
        if model == "Tümü":
            model = None
        saat = min(168, len(durum["test"]))
        figur = plots.gercek_vs_tahmin(durum["test"], durum["tahminler"], saat, model)
    elif secim in ("MAPE", "MAE"):
        figur = plots.model_karsilastirma(durum["sonuclar"], secim)
    else:
        if durum["onemler"] is None:
            bos_mesaj(w["karsilastir_alan"],
                      "Özellik önemi için Random Forest seçili olarak karşılaştırma yapın.")
            durum["figurler"].pop("karsilastirma", None)
            return
        figur = plots.ozellik_onemi(durum["onemler"])

    grafik_goster(w["karsilastir_alan"], figur, "karsilastirma")


def sonuc_kaydet_tiklandi():
    """Karsilastirma sonuclarini CSV dosyasina yazar."""
    if durum["sonuclar"] is None:
        messagebox.showwarning("Sonuç yok", "Önce karşılaştırmayı çalıştırın.")
        return
    yol = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="sonuclar.csv",
                                       filetypes=[("CSV dosyaları", "*.csv")])
    if not yol:
        return
    try:
        with open(yol, "w", encoding="utf-8", newline="") as dosya:
            yazici = csv.writer(dosya)
            yazici.writerow(["model", "MAPE", "MAE", "RMSE"])
            for isim, m in durum["sonuclar"].items():
                yazici.writerow([isim, round(m["MAPE"], 3), round(m["MAE"], 1),
                                 round(m["RMSE"], 1)])
    except OSError as e:
        messagebox.showerror("Kaydedilemedi", str(e))
        return
    durum_yaz("Sonuçlar kaydedildi: " + yol, RENK_BASARI)


def png_kaydet_tiklandi():
    """Karsilastirma sekmesindeki grafigi PNG olarak kaydeder."""
    figur = durum["figurler"].get("karsilastirma")
    if figur is None:
        messagebox.showwarning("Grafik yok", "Kaydedilecek bir grafik yok.")
        return
    yol = filedialog.asksaveasfilename(defaultextension=".png", initialfile="grafik.png",
                                       filetypes=[("PNG resmi", "*.png")])
    if not yol:
        return
    try:
        figur.savefig(yol, dpi=150)
    except (OSError, ValueError) as e:
        messagebox.showerror("Kaydedilemedi", str(e))
        return
    durum_yaz("Grafik kaydedildi: " + yol, RENK_BASARI)


# ---------------------------------------------------------------------------
# Ana pencere
# ---------------------------------------------------------------------------
def baslik_kur(pencere):
    """Pencerenin ustundeki koyu renkli baslik seridini olusturur."""
    serit = tk.Frame(pencere, bg=RENK_BASLIK, padx=20, pady=12)
    serit.pack(fill="x")
    tk.Label(serit, text="Elektrik Yük Tahmin Aracı", bg=RENK_BASLIK, fg="white",
             font=(YAZI, 20, "bold")).pack(anchor="w")
    tk.Label(serit, text="EEE303  •  Kısa vadeli saatlik yük tahmini (STLF)",
             bg=RENK_BASLIK, fg="#a9c1dd", font=(YAZI, 12)).pack(anchor="w")


def kapat():
    """Pencere kapatilinca Tkinter dongusunu duzgunce sonlandirir."""
    w["pencere"].quit()
    w["pencere"].destroy()


def main():
    """Ana pencereyi ve sekmeleri olusturup programi baslatir."""
    pencere = tk.Tk()
    pencere.title("EEE303 - Elektrik Yük Tahmin Aracı")
    pencere.geometry("1200x780")
    pencere.minsize(1000, 680)
    pencere.configure(bg=RENK_ARKA)
    w["pencere"] = pencere

    stil_ayarla(pencere)
    baslik_kur(pencere)

    # Durum cubugu en altta
    w["durum"] = tk.Label(pencere, text="Hazır. Başlamak için veri yükleyin.", anchor="w",
                          bg="#dfe5ee", fg=RENK_YAZI, padx=12, pady=4, font=(YAZI, 11))
    w["durum"].pack(side="bottom", fill="x")

    defter = ttk.Notebook(pencere)
    defter.pack(fill="both", expand=True, padx=12, pady=12)

    veri_sekmesi_kur(defter)
    kesif_sekmesi_kur(defter)
    tahmin_sekmesi_kur(defter)
    karsilastirma_sekmesi_kur(defter)

    pencere.protocol("WM_DELETE_WINDOW", kapat)
    pencere.mainloop()


if __name__ == "__main__":
    main()
