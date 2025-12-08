from fastapi import APIRouter, Depends
from src.api.core.operation.media import entryMedia, uploadImage
from src.api.models.rideModel import Ride, RideRead, UserRideFormCreate
from src.api.core import (
    GetSession,
    api_response,
    requireSignin,
    requireAdmin,
    requirePermission,
)

router = APIRouter(prefix="/ride", tags=["ride"])


@router.put("/create", response_model=RideRead)
async def update_user(
    user: requireSignin,
    session: GetSession,
    request: UserRideFormCreate = Depends(),
):
    user_id = user.get("id")

    if request.car_pic:
        files = [request.car_pic]
        saved_files = await uploadImage(files, thumbnail=False)

        records = entryMedia(session, saved_files)

        request.car_pic = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )
    if request.other_images:
        other_files = request.other_images
        saved_files = await uploadImage(other_files, thumbnail=False)

        records = entryMedia(session, saved_files)

        request.other_images = records

    if request.from_:
        request.from_location = {
            "type": "Point",
            "coordinates": [
                float(request.from_["longitude"]),
                float(request.from_["latitude"]),
            ],
        }

    if request.to_:
        request.to_location = {
            "type": "Point",
            "coordinates": [
                float(request.to_["longitude"]),
                float(request.to_["latitude"]),
            ],
        }
    print(request.__dict__)
    # ride = Ride(**request.model_dump())
    # ride.user_id = user_id
    # session.add(ride)
    # session.commit()
    # session.refresh(ride)
    return api_response(200, "Ride Create Successfully")
