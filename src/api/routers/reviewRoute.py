from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select
from src.api.core.operation import listRecords
from src.api.core.response import api_response, raiseExceptions
from src.api.models.reviewModel import Review, ReviewCreate, ReviewUpdate, ReviewRead
from src.api.core.dependencies import GetSession, ListQueryParams, requireSignin

router = APIRouter(prefix="/review", tags=["Review"])


@router.post("/create")
def create(
    request: ReviewCreate,
    session: GetSession,
    user: requireSignin,
):
    review = Review(
        reviewer_id=user.get("id"),
        target_id=request.target_id,
        rating=request.rating,
        comment=request.comment,
    )

    session.add(review)
    session.commit()
    session.refresh(review)

    return api_response(
        200,
        "Review Created Successfully",
        ReviewRead.model_validate(review),
    )


@router.put("/update/{id}")
def update(
    id: int,
    request: ReviewUpdate,
    session: GetSession,
    user: requireSignin,
):
    review = session.exec(
        select(Review).where(
            Review.id == id,
            Review.reviewer_id == user.get("id"),
        )
    ).first()

    raiseExceptions((review, 404, "Review not found"))

    if request.rating is not None:
        review.rating = request.rating
    if request.comment is not None:
        review.comment = request.comment

    session.commit()
    session.refresh(review)

    return api_response(
        200,
        "Review Updated Successfully",
        ReviewRead.model_validate(review),
    )


@router.delete("/delete/{id}")
def delete(
    id: int,
    target_id: int,
    session: GetSession,
    user: requireSignin,
):
    review = session.exec(
        select(Review).where(
            Review.id == id,
            Review.reviewer_id == user.get("id"),
            Review.target_id == target_id,
        )
    ).first()

    raiseExceptions((review, 404, "Review not found"))

    session.delete(review)
    session.commit()

    return api_response(200, "Review Deleted Successfully")


@router.get("/list/{user_id}")
def list_reviews(
    user_id: int,
    session: GetSession,
    query_params: ListQueryParams,
):
    query_params = vars(query_params)

    response = listRecords(
        query_params=query_params,
        searchFields=["comment"],
        customFilters=[["target_id", user_id]],
        Model=Review,
    )

    list_data = [
        ReviewRead.model_validate(prod).model_dump() for prod in response["data"]
    ]

    stats = session.exec(
        select(
            func.avg(Review.rating),
            func.count(Review.id),
            func.min(Review.updated_at),
        ).where(Review.target_id == user_id)
    ).one()

    data = {
        "list": list_data,  # ✅ already serialized
        "extra": {
            "averageRating": float(stats[0] or 0),
            "totalReviews": stats[1],
            "startDate": stats[2],
        },
    }

    return api_response(
        200,
        "data found",
        data,
        response["total"],
    )
