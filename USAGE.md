# Neptune Pool Payouts Manager - Инструкция по использованию

## Описание

Простое веб-приложение для управления выплатами Neptune Pool с использованием команды `neptune-cli send-to-many`.

## Доступ

Веб-интерфейс: **http://172.16.0.180:5001**

## Компоненты системы

### База данных

1. **VIEW: `pending_payments_grouped`** - агрегирует pending платежи по адресам майнеров
2. **Таблица: `payout_batches`** - логи всех массовых выплат
3. **Функция: `record_payout_batch()`** - записывает выполненную выплату и обновляет статусы

### Веб-интерфейс

#### Вкладка "Новые выплаты"
- Таблица pending платежей с группировкой по кошелькам
- Настройка комиссии транзакции
- Генерация команды neptune-cli send-to-many
- Автоматическое выполнение выплаты

#### Вкладка "История"
- Последние 50 выплат с tx hash и статусами

## Workflow выплаты

1. Открыть http://172.16.0.180:5001
2. Проверить список pending платежей
3. При необходимости изменить комиссию (по умолчанию 0.001 NPT)
4. Нажать "Сгенерировать команду"
5. Проверить команду
6. Нажать "Выполнить выплату" и подтвердить
7. Дождаться результата
8. Проверить обновление в истории

## Управление сервисом

```bash
systemctl status neptune-payouts
systemctl start neptune-payouts
systemctl stop neptune-payouts
systemctl restart neptune-payouts
journalctl -u neptune-payouts -f
```

## API Endpoints

- GET `/api/pending-payments` - список платежей
- POST `/api/generate-command` - генерация команды
- POST `/api/execute-payout` - выполнение выплаты
- GET `/api/payout-history` - история выплат
