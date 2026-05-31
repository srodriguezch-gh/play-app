"""Task and reward management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Task, Transaction, Player, Wallet, get_session

router = APIRouter(prefix="/api", tags=["tasks"])


class TaskCreate(BaseModel):
    child_name: str
    task_description: str
    points: int = 1
    is_recurring: bool = False
    series_total: int = 1


class TaskUpdate(BaseModel):
    is_completed: bool | None = None
    is_approved: bool | None = None
    series_count: int | None = None
    pin: str | None = None


class ApproveRequest(BaseModel):
    approved: bool
    pin: str


class TransactionCreate(BaseModel):
    child_name: str
    amount: float
    description: str | None = None


VALID_CHILDREN = {"Emma", "Mateo", "Dad"}


async def _get_or_create_wallet(session: AsyncSession, child: str) -> Wallet:
    wallet = await session.get(Wallet, child)
    if wallet is None:
        wallet = Wallet(player_name=child, balance=0)
        session.add(wallet)
        await session.flush()
    return wallet


@router.get("/tasks/{child}")
async def get_tasks(child: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Task).where(Task.child_name == child).order_by(Task.created_at.desc())
    )
    return result.scalars().all()


@router.post("/tasks")
async def create_task(data: TaskCreate, session: AsyncSession = Depends(get_session)):
    if data.child_name not in VALID_CHILDREN:
        raise HTTPException(status_code=400, detail="Invalid child_name")
    if not data.task_description or len(data.task_description) > 500:
        raise HTTPException(status_code=400, detail="Invalid task_description")
    task = Task(
        child_name=data.child_name,
        task_description=data.task_description.strip(),
        points=data.points,
        is_recurring=data.is_recurring,
        series_total=data.series_total,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, data: TaskUpdate, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if data.is_approved is not None:
        raise HTTPException(status_code=400, detail="Use /approve endpoint for approvals")
    elif data.series_count is not None:
        if task.is_recurring and task.last_increment_at:
            last = task.last_increment_at
            now = datetime.utcnow()
            if last.date() == now.date():
                raise HTTPException(status_code=403, detail="Only 1 event per day for recurring tasks")
        task.series_count = data.series_count
        task.is_completed = data.series_count >= task.series_total
        task.is_approved = False
        task.last_increment_at = datetime.utcnow()
    elif data.is_completed is not None:
        task.is_completed = data.is_completed
        task.is_approved = False

    await session.commit()
    await session.refresh(task)
    return task


from core.auth import verify_pin

@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: int, data: ApproveRequest, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await session.execute(select(Player).where(Player.name == task.child_name))
    player = result.scalars().one_or_none()
    if not player or not player.pin:
        raise HTTPException(status_code=403, detail="No PIN set for this player")

    if not verify_pin(data.pin, player.pin):
        raise HTTPException(status_code=401, detail="Incorrect PIN")

    task.is_approved = data.approved
    if data.approved:
        task.is_completed = True

        wallet = await _get_or_create_wallet(session, task.child_name)
        wallet.balance = (wallet.balance or 0) + task.points
        session.add(Transaction(
            child_name=task.child_name,
            amount=task.points,
            description=f"Approved task: {task.task_description}",
            kind="earn",
        ))

    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(task)
    await session.commit()
    return {"success": True}


@router.get("/transactions/{child}")
async def get_transactions(child: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Transaction).where(Transaction.child_name == child).order_by(Transaction.created_at.desc())
    )
    return result.scalars().all()


@router.post("/transactions")
async def create_transaction(data: TransactionCreate, session: AsyncSession = Depends(get_session)):
    wallet = await _get_or_create_wallet(session, data.child_name)
    wallet.balance = (wallet.balance or 0) + data.amount
    tx = Transaction(
        child_name=data.child_name,
        amount=data.amount,
        description=data.description,
        kind="earn" if data.amount >= 0 else "spend",
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


@router.post("/payout/{child}")
async def payout(child: str, session: AsyncSession = Depends(get_session)):
    await session.execute(
        update(Task).where(
            Task.child_name == child,
            Task.is_completed == True,
            Task.is_approved == True,
            Task.is_paid == False,
        ).values(is_paid=True)
    )
    await session.commit()
    return {"success": True}
