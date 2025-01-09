# Testing Commands for the Discord Bot

## **Basic Commands**

### 1. `!hello`
**Expected Output:**
```
Hello, world!
```

### 2. `!ping`
**Expected Output:**
```
Pong!
```

### 3. `!say "Test message"`
**Expected Output:**
```
Test message
```

---

## **Help Command**

### 4. `!myhelp`
**Expected Output:**
```
**Commandes disponibles :**
- `!schedule <title> <date> <time>` : Planifier un rappel.
- `!reminders` : Voir tous vos rappels.
- `!delete <ID>` : Supprimer un rappel spécifique.
```

---

## **Reminder Management Commands**

### 5. `!schedule "Meeting" "2025-01-10" "15:00"`
**Expected Output:**
```
✅ Rappel planifié : Meeting le 2025-01-10 à 15:00. (ID: <unique-ID>)
```

### 6. `!reminders`
**Expected Output:**
```
**Vos rappels :**
1. **Meeting** - 2025-01-10 15:00 (ID: <unique-ID>)
```

### 7. `!delete <unique-ID>`
**Expected Output:**
```
✅ Rappel supprimé : Meeting (ID: <unique-ID>)
```

### 8. `!reminders`
**Expected Output:**
```
Vous n'avez aucun rappel.
```

---

## **Edge Case Testing**

### 9. `!say` (without a message)
**Expected Output:**
```
Commande incorrecte. Veuillez inclure un message.
```

### 10. `!schedule "InvalidDate" "date" "time"`
**Expected Output:**
```
❌ Une erreur est survenue lors de la planification du rappel.
```

### 11. `!delete InvalidID`
**Expected Output:**
```
❌ ID de rappel invalide. Veuillez vérifier vos rappels avec !reminders.
```

---

## **Bot Initialization Test**

### 12. Run the bot
**Expected Console Output:**
```
Répertoire courant : <current-directory>
Bot connecté en tant que <bot-name>
```


