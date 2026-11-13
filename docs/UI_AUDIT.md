# Audit Fungsi UI

Status per halaman: elemen interaktif utama dan tes yang membuktikan fungsinya. Semua lulus pada 134 tes.

| Halaman | Elemen | Bukti |
|---|---|---|
| Mulai di Sini | Tombol utama "Langkah berikutnya" (4 kondisi), "Atur aturan sendiri" | `test_ui_start_here_next_action_conditions`, `test_ui_demo_scenario_loader` |
| Dasbor | Proyek baru, Ekspor, Impor, Reset Topologi; tabel uji | `test_ui_overview_renders_after_demo_with_audit_log`, `test_overview_recent_tests_table_uses_device_names` |
| Topologi 2D | Tambah perangkat, hubungkan kabel (Fa/Se, port), hapus, seret, reset posisi | `test_network_inspector_selectbox_keeps_user_choice`, `test_workspace.py` |
| Konfigurasi Perangkat | Pilih perangkat, gateway, IP interface, status port | `test_device_config_selectbox_changes_selected_device`, `test_device_config_invalid_ip_is_not_saved` |
| Aturan Firewall | Default policy, Naik/Turun, Matikan, Hapus (dialog), Tambah | `test_rules_toggle_marks_rule_nonaktif_in_text`, `test_rules_move_down_swaps_order`, `test_rules_add_rule_from_device_choice` |
| Simulasi Paket | Uji cepat, paket kustom, Lihat di 3D/Log, Hapus riwayat | `test_packet_sim_quick_test_adds_result_and_view_in_3d_selects_it`, `test_packet_sim_custom_manual_ip_requires_value` |
| Visualisasi 3D | Pilih hasil, replay, tanpa ID internal | `test_ui_3d_viz_renders_with_history`, `test_viz3d_panel_and_selector_have_no_internal_ids` |
| Log Trafik | Filter keputusan, pencarian nama, Kosongkan log | `test_logs_filter_by_decision`, `test_logs_search_accepts_device_name` |
| Pusat Peringatan | Tandai ditinjau, kosongkan, catatan "bukan serangan" | `test_alerts_keep_policy_notice_and_can_acknowledge` |
| Lab Belajar | Muat dan uji, Muat saja, penilaian Lulus | `test_lab_load_and_test_reports_pass_and_clears_old_results` |
| Konsol CLI | Mode, prompt, perintah, chip, ping | `test_ios_cli.py`, `test_pages_cli.py` |

Elemen lama yang tidak berfungsi dihapus: pilihan Mode Belajar/Profesional.
