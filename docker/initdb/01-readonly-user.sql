-- Dijalankan otomatis oleh image postgres saat data directory pertama kali dibuat.
--
-- Skrip ini HANYA membuat role dan hak koneksi. Pemberian SELECT per objek
-- dilakukan aplikasi di init_db() setelah tabel dan view terbentuk — lihat
-- `terapkan_hak_readonly` di backend/database.py. Sengaja tidak memakai
-- ALTER DEFAULT PRIVILEGES, karena itu akan ikut memberi SELECT pada tabel
-- `users` dan `chat_history` yang justru harus tertutup bagi SQL tool.

CREATE ROLE sva_readonly LOGIN PASSWORD 'readonly_secret';

GRANT CONNECT ON DATABASE agentic_rag TO sva_readonly;
GRANT USAGE ON SCHEMA public TO sva_readonly;
