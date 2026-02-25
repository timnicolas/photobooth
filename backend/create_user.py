#!/usr/bin/env python3
"""Script pour créer un compte utilisateur (admin ou normal)."""
import getpass

from werkzeug.security import generate_password_hash

from api.models import User, init_db


def main():
    init_db()

    print("=== Création d'un compte utilisateur ===\n")

    mail = input("Email : ").strip()
    if not mail:
        print("Erreur : l'email ne peut pas être vide.")
        return

    if User.select().where(User.mail == mail).exists():
        print(f"Erreur : un utilisateur avec l'email '{mail}' existe déjà.")
        return

    firstname = input("Prénom : ").strip()
    lastname = input("Nom : ").strip()

    password = getpass.getpass("Mot de passe : ")
    if not password:
        print("Erreur : le mot de passe ne peut pas être vide.")
        return

    confirm = getpass.getpass("Confirmer le mot de passe : ")
    if password != confirm:
        print("Erreur : les mots de passe ne correspondent pas.")
        return

    role = input("Rôle [admin/user] (défaut : user) : ").strip().lower()
    if role not in ("admin", "user", ""):
        print("Erreur : rôle invalide. Choisir 'admin' ou 'user'.")
        return
    is_admin = role == "admin"

    User.create(
        mail=mail,
        firstname=firstname,
        lastname=lastname,
        password=generate_password_hash(password),
        is_admin=is_admin,
    )

    label = "admin" if is_admin else "utilisateur"
    print(f"\nCompte {label} créé : {firstname} {lastname} ({mail})")


if __name__ == "__main__":
    main()
