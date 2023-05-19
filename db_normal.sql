CREATE DATABASE IF NOT EXISTS optikoe;
USE optikoe;

CREATE TABLE IF NOT EXISTS users(
    id_user INT NOT NULL,
    nama VARCHAR(29) NOT NULL,
    email VARCHAR(30) NOT NULL,
    no_hp VARCHAR(15) NOT NULL,
    password VARCHAR(30) NOT NULL,
    id_role INT,
    id_bentuk_muka INT,
    path_foto VARCHAR(40),
    alamat VARCHAR(50),
    tanggal_pendaftaran TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id_user)
);

CREATE TABLE IF NOT EXISTS toko(
    id_toko INT NOT NULL,
    nama_toko VARCHAR(20) NOT NULL,
    path_foto VARCHAR(40),
    rating FLOAT,
    id_user INT NOT NULL,
    deskripsi VARCHAR(50),
    tanggal_pendaftaran TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id_toko)
);

CREATE TABLE IF NOT EXISTS roles(
    id_role INT NOT NULL,
    nama_role VARCHAR(10) NOT NULL,

    PRIMARY KEY (id_role)
);

CREATE TABLE IF NOT EXISTS bentuk_muka(
    id_bentuk_muka INT NOT NULL,
    bentuk_muka VARCHAR(10) NOT NULL,

    PRIMARY KEY (id_bentuk_muka)
);

CREATE TABLE IF NOT EXISTS produk(
    id_produk INT NOT NULL,
    id_toko INT NOT NULL,
    nama_produk VARCHAR(30) NOT NULL,
    id_bentuk_kacamata INT, 
    harga BIGINT NOT NULL,
    deskripsi VARCHAR(50),
    stok INT,
    is_active BOOLEAN,

    PRIMARY KEY (id_produk)
);

CREATE TABLE IF NOT EXISTS rating(
    id_rating INT NOT NULL,
    id_user INT NOT NULL,
    id_produk INT NOT NULL,
    nilai_rating INT NOT NULL,
    komentar VARCHAR(50),

    PRIMARY KEY(id_rating)
);

CREATE TABLE IF NOT EXISTS foto_produk(
    id_foto_produk INT NOT NULL,
    id_produk INT NOT NULL,
    path_foto VARCHAR(40),

    PRIMARY KEY (id_foto_produk)
);

CREATE TABLE IF NOT EXISTS bentuk_kacamata(
    id_bentuk_kacamata INT NOT NULL,
    bentuk_kacamata VARCHAR(10) NOT NULL,

    PRIMARY KEY (id_bentuk_kacamata)
);

CREATE TABLE IF NOT EXISTS status_history(
    id_status INT NOT NULL,
    nama_status VARCHAR(10) NOT NULL,

    PRIMARY KEY (id_status)
);

CREATE TABLE IF NOT EXISTS history(
    id_history INT NOT NULL,
    id_user INT NOT NULL,
    id_produk INT NOT NULL,
    tanggal TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    jumlah_produk INT unsigned NOT NULL,
    id_status INT NOT NULL,

    PRIMARY KEY (id_history)
);

CREATE TABLE IF NOT EXISTS kecocokan(
    id_kecocokan INT NOT NULL, 
    id_bentuk_muka INT NOT NULL,
    id_bentuk_kacamata INT NOT NULL,

    PRIMARY KEY(id_kecocokan)
);

-- FOREIGN KEY WITHOUT CONNECTING TO FIREBASE
ALTER TABLE users
ADD FOREIGN KEY (id_role) REFERENCES roles(id_role),
ADD FOREIGN KEY (id_bentuk_muka) REFERENCES bentuk_muka(id_bentuk_muka);

ALTER TABLE toko 
ADD FOREIGN KEY (id_user) REFERENCES users(id_user);

ALTER TABLE produk
ADD FOREIGN KEY (id_toko) REFERENCES toko(id_toko),
ADD FOREIGN KEY (id_bentuk_kacamata) REFERENCES bentuk_kacamata(id_bentuk_kacamata);

ALTER TABLE foto_produk
ADD FOREIGN KEY (id_produk) REFERENCES produk(id_produk);

ALTER TABLE rating
ADD FOREIGN KEY (id_user) REFERENCES users(id_user),
ADD FOREIGN KEY (id_produk) REFERENCES produk(id_produk);

ALTER TABLE history
ADD FOREIGN KEY (id_produk) REFERENCES produk(id_produk),
ADD FOREIGN KEY (id_status) REFERENCES status_history (id_status),
ADD FOREIGN KEY (id_user) REFERENCES users(id_user);

ALTER TABLE kecocokan
ADD FOREIGN KEY (id_bentuk_kacamata) REFERENCES bentuk_kacamata(id_bentuk_kacamata),
ADD FOREIGN KEY (id_bentuk_muka) REFERENCES bentuk_muka(id_bentuk_muka);