# Charge Wallet V1

현재 구현 범위는 `wallet / charge_orders / wallet_ledger` 백엔드 골격과 조회 API까지입니다.

## 포함된 것

- `users.balance` 와 동기화되는 `wallets`
- 실제 충전 주문 상태를 담는 `charge_orders`
- 충전/주문차감/관리자조정을 남기는 `wallet_ledger`
- 기존 `balance_transactions` 를 `wallet_ledger` 로 백필하는 동기화 로직
- 신규 API
  - `GET /api/wallet`
  - `GET /api/wallet/ledger`
  - `GET /api/charge-orders`
  - `GET /api/charge-orders/{id}`
  - `POST /api/charge-orders`

## 현재 상태

- 기존 `POST /api/charge` 는 호환을 위해 유지되며, 내부적으로 `charge_orders` 를 만든 뒤 즉시 완료 처리합니다.
- 카드/간편결제/계좌입금용 실제 PG 연동은 아직 붙지 않았습니다.
- `POST /api/charge-orders` 는 결제 주문만 생성하고, 카드 승인/가상계좌 확정/웹훅 반영 단계는 다음 턴 범위입니다.

## 다음 작업 우선순위

1. 고객용 `충전하기 / 이용내역` 새 UI 연결
2. `POST /api/charge-orders/{id}/confirm`
3. `POST /api/payments/webhook`
4. 계좌입금/가상계좌 승인 흐름
5. 관리자 충전 주문 승인/실패/환불 처리

## 구현 메모

- 현재 코드베이스는 `users.balance` 를 주문 차감 로직 전반에서 직접 사용하고 있습니다.
- 이번 단계에서는 회귀를 줄이기 위해 `wallets.available_balance` 를 `users.balance` 와 동기화하는 방식으로 도입했습니다.
- 최종적으로는 주문 차감과 관리자 조정도 `wallets + wallet_ledger` 기준으로 정리하는 것이 좋습니다.
