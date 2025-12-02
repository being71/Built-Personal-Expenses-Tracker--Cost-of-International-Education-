1. Untuk Living-Cost-index itu baselinenya dari New York
2. Tuition_USD itu untuk 1 tahun
3. Rent_USD itu per 1 bulan jadi harus di x12 dulu
4. Visa_Fee_USD ini anggapannya per 1 tahun jadi harus disesuaikan Visa_Fee_USD * Duration_Years
5. exchange_rate itu pada USD!

Berikut ringkasan keadaan project saat ini
   yang bisa Anda pakai sebagai konteks besok:
⛬  Ringkasan Keadaan Project Saat Ini

   1. Struktur Aplikasi

   •  Aplikasi berbasis Flask
      (views/__init__.py) dengan route utama:
     •  / → home.html (landing page).
     •  /budget-planning → perencanaan anggaran       
         individual per universitas.
     •  /policy-analysis → analisis kebijakan &
         affordability sistemik.
     •  /economic-research dan
        /university-benchmarking → halaman
        placeholder/template.
   •  Sumber data utama:
      International_Education_Costs.csv di
      root.

   ──────────────────────────────────────────

   2. Halaman Home

   •  home.html menampilkan:
     •  Hero section dengan deskripsi singkat
        produk.
     •  Tombol utama:
       •  Open Budget Planner →
          /budget-planning.
       •  View Benchmarking →
          /university-benchmarking.
     •  Grid kartu fitur:
       •  Budget Planning, Policy Analysis,
          Economic Research, University
          Benchmarking.
   •  UI memakai tema dark glass dengan
      Bootstrap 5 dan styles.css.

   ──────────────────────────────────────────

   3. Budget Planning (Individual)

   •  Menggunakan CSV untuk daftar universitas;       
       user pilih universitas + isi:
     •  New York annual living cost (opsional,        
        default 26.000 USD).
     •  Inflasi biaya hidup tahunan.
   •  Backend (feature/budget_planning.py)
      menghitung:
     •  Biaya per tahun, total program, dampak        
        inflasi, dsb.
   •  Menghasilkan grafik insight (disimpan
      sebagai PNG di views/static) untuk 1
      universitas terpilih.

   ──────────────────────────────────────────

   4. Policy Analysis – State Saat Ini

   4.1. Struktur Umum

   •  Template:
      views/templates/policy_analysis.html.
   •  Di atas halaman:
     •  Floating menu button (☰ Menu) di kiri
        atas (fixed, selalu mengikuti scroll)
        yang membuka offcanvas:
       •  Home
       •  Budget Planning
       •  Policy Analysis (aktif)
       •  Economic Research
       •  University Benchmarking
     •  Header kanan: dropdown View:
       •  Insight Charts
       •  Policy User Input
     •  Judul (rata kiri, seperti awal):
       ```html
       <h1>Policy Analysis</h1>
       <small>System-level view of
   affordability and policy gaps.</small>
       ```

   4.2. Mode tampilan (dropdown View)

   •  Insight Charts:
     •  Panel deskripsi awal (baseline NY
        living cost dan definisi affordability        
        index).
     •  Policy insight charts:
       1. Direct vs indirect annual costs
         •  Backend (generate_policy_charts)
             sekarang memakai definisi
            kebijakan:
           •  Direct = tuition +
              visa/durasi + insurance.
           •  Living-related = rent (×12)
              + komponen dari
              Living_Cost_Index.
         •  Satu gambar dengan 2 panel:
           •  Kiri: total annual cost top
              10 program (stacked bar:
              direct vs living).
           •  Kanan: komposisi persentase
              direct vs living (100%
              stacked).
       2. Economic context
         •  Bar horizontal per negara:
           •  Panjang bar = living cost 
              index rata-rata.
           •  Warna bar (colormap RdYlGn)
              = affordability index:
             •  Hijau = lebih
                affordable.
             •  Merah = kurang
                affordable.
       3. Costs by level and duration
         •  Multi-panel figure:
           •  Boxplot annual cost per
              Level (Bachelor/Master/PhD).
           •  Line chart hubungan
              Duration_Years vs median 
              annual cost per level.
           •  Ranking cost per year
              (total/Duration) top 15
              program.
           •  Small multiples bar chart
              per level (top program
              paling mahal per level).
     •  Tabel:
       •  Most affordable programmes (top 10
          by affordability_index).
       •  Policy gap by country & level (avg
          cost, avg affordability, share di
          atas median).

   •  Policy User Input:
     •  Form GET:
       •  target_annual (target biaya
          tahunan).
       •  tuition_cut (% diskon tuition).
       •  living_subsidy (% subsidi biaya
          hidup).
     •  Validasi input (angka, range 0–100,
        dsb).
     •  Backend (feature/policy_analysis.py):
       •  apply_policy_scenario menerapkan
          skenario ke semua program.
       •  compute_target_gap_tables
          menghitung:
         •  Tabel program yang masih di atas
             target.
         •  Tabel agregat by country & level
             plus komposisi tuition vs
            living.
     •  Tabel di UI:
       •  Gap to target after policy levers
          (top program di atas target).
       •  Where the gap comes from (gap
          rata-rata, share di atas target, dan        
           komposisi tuition vs living).

   ──────────────────────────────────────────

   5. Logika Backend Policy Analysis (ringkas)        

   •  build_policy_frame(df, ny_living):
     •  Hitung:
       •  direct_annual_usd,
          indirect_annual_usd (via living
          index × NY baseline),
          total_annual_usd.
       •  affordability_index (lebih tinggi =
          lebih affordable).
       •  policy_gap_usd (deviasi dari median
          per level).
   •  summarize_policy_insights(frame):
     •  total_annual, affordability,
        policy_gap, comparative (by country).
   •  generate_policy_charts(frame, STATIC_DIR,       
       "policy"):
     •  cost_components.png → direct vs living        
        (dengan definisi kebijakan).
     •  economic_context.png → living index by        
        country (warna = affordability).
     •  institution_program.png → multi-panel
        level/duration/effisiensi.
   •  apply_policy_scenario dan
      compute_target_gap_tables menggerakkan
      mode Policy User Input.

   ──────────────────────────────────────────

   6. Styling & Navigasi

   •  styles.css:
     •  Tema dark, glass, gradient background.        
     •  Komponen khusus:
       •  .floating-menu-toggle → tombol menu
          melayang kiri atas (offcanvas).
       •  Kustomisasi form, tabel, panel,
          hero, dsb.
   •  Bootstrap 5 (CSS + bundle JS) digunakan
      dari CDN untuk:
     •  Grid, tombol, offcanvas, dsb.

   ──────────────────────────────────────────

   7. Status Teknis

   •  File Python utama (views/__init__.py,
      feature/policy_analysis.py) sudah dicek
      dengan python3 -m py_compile → tidak ada        
      error sintaks.
   •  Tidak ada konfigurasi test/unit test
      otomatis yang jelas di repo (tidak ada
      pytest.ini, tests/, dll. dari pencarian
      sebelumnya).
   •  Banyak file PNG chart telah dihasilkan di       
       views/static/ (budget & policy charts).        

   ──────────────────────────────────────────

   8. Hal yang Perlu Diingat Saat Lanjut Besok        

   •  Navigasi:
     •  Tombol back sudah diganti dengan
        floating “☰ Menu” yang membuka
        offcanvas berisi seluruh menu utama.
   •  Interpretasi warna:
     •  Economic context: hijau = affordability       
         tinggi (lebih affordable), merah =
        rendah.
   •  Direct vs indirect:
     •  Grafik sudah menggunakan definisi 
        kebijakan (tuition+visa+insurance vs
        rent+living); rumus inti affordability        
        di data masih seperti semula.
   •  Jika mau lanjut besok, area yang paling
      natural untuk dikembangkan/dirapikan:
     •  Penjelasan naratif di bawah tiap grafik       
         (bila ingin diperkuat lagi).
     •  Menambah filter (by level, country) di        
        Policy Analysis.
     •  Menambahkan test ringan (misalnya
        script untuk cek basic integrity CSV
        dan output frame).