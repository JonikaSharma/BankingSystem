
import sqlite3
import uuid
from decimal import Decimal, InvalidOperation

DB_NAME = "bank.db"


# ---------------- DATABASE CONNECTION ----------------

def connect():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_no TEXT PRIMARY KEY,
            holder_name TEXT NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_no) REFERENCES accounts(account_no)
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HELPER FUNCTIONS ----------------

def money_input():
    """Convert user input into integer paise."""
    try:
        amount = Decimal(input("Enter amount (Rs.): ").strip())

        if not amount.is_finite() or amount <= 0:
            print("Please enter a valid positive amount.")
            return None

        if amount != amount.quantize(Decimal("0.01")):
            print("Maximum two decimal places are allowed.")
            return None

        return int(amount * 100)

    except InvalidOperation:
        print("Invalid amount. Please enter a number.")
        return None


def format_money(paise):
    return f"Rs. {paise / 100:,.2f}"


def account_exists(account_no):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT account_no FROM accounts WHERE account_no = ?",
        (account_no,)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None


# ---------------- CREATE ACCOUNT ----------------

def create_account():
    print("\n========== CREATE ACCOUNT ==========")

    name = input("Enter account holder name: ").strip()

    if not name:
        print("Name cannot be empty.")
        return

    account_no = "BANK" + uuid.uuid4().hex[:10].upper()

    conn = connect()

    try:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT INTO accounts
            (account_no, holder_name, balance)
            VALUES (?, ?, 0)
        """, (account_no, name))

        conn.commit()

        print("\nAccount created successfully!")
        print("Account Holder:", name)
        print("Account Number:", account_no)
        print("Initial Balance: Rs. 0.00")

    except sqlite3.Error as error:
        conn.rollback()
        print("Error creating account:", error)

    finally:
        conn.close()


# ---------------- DEPOSIT MONEY ----------------

def deposit_money():
    print("\n========== DEPOSIT MONEY ==========")

    account_no = input("Enter account number: ").strip().upper()

    amount = money_input()

    if amount is None:
        return

    conn = connect()

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.cursor()

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_no = ?",
            (account_no,)
        )

        account = cursor.fetchone()

        if account is None:
            print("Account not found.")
            conn.rollback()
            return

        new_balance = account[0] + amount

        cursor.execute("""
            UPDATE accounts
            SET balance = ?
            WHERE account_no = ?
        """, (new_balance, account_no))

        cursor.execute("""
            INSERT INTO transactions
            (account_no, transaction_type, amount, balance_after)
            VALUES (?, 'DEPOSIT', ?, ?)
        """, (account_no, amount, new_balance))

        conn.commit()

        print("\nDeposit successful!")
        print("Deposited:", format_money(amount))
        print("Available Balance:", format_money(new_balance))

    except sqlite3.Error as error:
        conn.rollback()
        print("Transaction failed:", error)

    finally:
        conn.close()


# ---------------- WITHDRAW MONEY ----------------

def withdraw_money():
    print("\n========== WITHDRAW MONEY ==========")

    account_no = input("Enter account number: ").strip().upper()

    amount = money_input()

    if amount is None:
        return

    conn = connect()

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.cursor()

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_no = ?",
            (account_no,)
        )

        account = cursor.fetchone()

        if account is None:
            print("Account not found.")
            conn.rollback()
            return

        current_balance = account[0]

        if amount > current_balance:
            print("Insufficient balance!")
            print("Available Balance:", format_money(current_balance))
            conn.rollback()
            return

        new_balance = current_balance - amount

        cursor.execute("""
            UPDATE accounts
            SET balance = ?
            WHERE account_no = ?
        """, (new_balance, account_no))

        cursor.execute("""
            INSERT INTO transactions
            (account_no, transaction_type, amount, balance_after)
            VALUES (?, 'WITHDRAWAL', ?, ?)
        """, (account_no, amount, new_balance))

        conn.commit()

        print("\nWithdrawal successful!")
        print("Withdrawn:", format_money(amount))
        print("Remaining Balance:", format_money(new_balance))

    except sqlite3.Error as error:
        conn.rollback()
        print("Transaction failed:", error)

    finally:
        conn.close()


# ---------------- CHECK ACCOUNT DETAILS ----------------

def check_balance():
    print("\n========== ACCOUNT DETAILS ==========")

    account_no = input("Enter account number: ").strip().upper()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT account_no, holder_name, balance, created_at
        FROM accounts
        WHERE account_no = ?
    """, (account_no,))

    account = cursor.fetchone()
    conn.close()

    if account is None:
        print("Account not found.")
        return

    print("\nAccount Information")
    print("--------------------------------")
    print("Account Number:", account[0])
    print("Account Holder:", account[1])
    print("Current Balance:", format_money(account[2]))
    print("Created On:", account[3])
    print("--------------------------------")


# ---------------- TRANSACTION HISTORY ----------------

def transaction_history():
    print("\n========== TRANSACTION HISTORY ==========")

    account_no = input("Enter account number: ").strip().upper()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT holder_name
        FROM accounts
        WHERE account_no = ?
    """, (account_no,))

    account = cursor.fetchone()

    if account is None:
        print("Account not found.")
        conn.close()
        return

    print("\nAccount Holder:", account[0])
    print("Account Number:", account_no)

    cursor.execute("""
        SELECT transaction_id,
               transaction_type,
               amount,
               balance_after,
               transaction_date
        FROM transactions
        WHERE account_no = ?
        ORDER BY transaction_id DESC
    """, (account_no,))

    records = cursor.fetchall()
    conn.close()

    if not records:
        print("\nNo transactions found.")
        return

    print("\n" + "-" * 85)
    print(f"{'ID':<6}{'TYPE':<15}{'AMOUNT':<17}"
          f"{'BALANCE':<17}{'DATE':<25}")
    print("-" * 85)

    for record in records:
        print(
            f"{record[0]:<6}"
            f"{record[1]:<15}"
            f"{format_money(record[2]):<17}"
            f"{format_money(record[3]):<17}"
            f"{record[4]:<25}"
        )

    print("-" * 85)


# ---------------- MAIN MENU ----------------

def main():
    initialize_database()

    while True:
        print("\n")
        print("=" * 45)
        print("       PYTHON BANKING MANAGEMENT SYSTEM")
        print("=" * 45)

        print("1. Create New Account")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Check Account Details")
        print("5. View Transaction History")
        print("6. Exit")

        print("=" * 45)

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            create_account()

        elif choice == "2":
            deposit_money()

        elif choice == "3":
            withdraw_money()

        elif choice == "4":
            check_balance()

        elif choice == "5":
            transaction_history()

        elif choice == "6":
            print("\nThank you for using our Banking System!")
            print("Goodbye!")
            break

        else:
            print("Invalid choice! Please select 1-6.")


# ---------------- PROGRAM ENTRY POINT ----------------

if __name__ == "__main__":
    main()
