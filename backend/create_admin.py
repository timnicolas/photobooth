#!/usr/bin/env python3
"""Script pour créer un compte administrateur."""
import getpass

from werkzeug.security import generate_password_hash

from api.models import User, init_db


def main():
    init_db()

    print("=== Création d'un compte administrateur ===\n")

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

    User.create(
        mail=mail,
        firstname=firstname,
        lastname=lastname,
        password=generate_password_hash(password),
        is_admin=True,
    )

    print(f"\nCompte admin créé : {firstname} {lastname} ({mail})")


if __name__ == "__main__":
    main()
