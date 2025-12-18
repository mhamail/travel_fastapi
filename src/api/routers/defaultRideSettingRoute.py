from datetime import datetime, timezone
import json
from typing import List
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlmodel import select
from src.api.core.dependencies import ListQueryParams
from src.api.core.response import raiseExceptions
from src.api.core.utility import parse_date, parse_list
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.operation.media import delete_media_items, entryMedia, uploadImage
from src.api.models.defaultRideSettingModel import (
    DefaultRideSetting,
    DefaultRideSettingRead,
    DefaultRideSettingForm,
)
from src.api.core import (
    GetSession,
    api_response,
    requireSignin,
    requireAdmin,
    requirePermission,
)

router = APIRouter(prefix="/default-ride-setting", tags=["default-ride-setting"])


@router.post("/create", response_model=DefaultRideSettingRead)
async def create_default_ride(
    user: requireSignin,
    session: GetSession,
    request: DefaultRideSettingForm = Depends(),
):
    user_id = user.get("id")

    if request.car_pic:
        files = [request.car_pic]
        saved_files = await uploadImage(files, thumbnail=False)

        records = entryMedia(session, saved_files)

        request.car_pic = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )

    # Add user_id
    ride_data = serialize_obj(request)
    ride_data["user_id"] = user_id

    if "arrival_time" in ride_data:
        ride_data["arrival_time"] = parse_date(ride_data["arrival_time"])

    # Create DefaultRideSetting instance
    ride = DefaultRideSetting(**ride_data)
    session.add(ride)
    session.commit()
    session.refresh(ride)
    print("typeof", type(ride))
    # ride_json = jsonable_encoder(RideRead.model_validate(ride))
    return api_response(200, "Default Ride Setting Create Successfully", ride)


@router.put("/update/{ride_id}", response_model=DefaultRideSettingRead)
async def update_ride(
    ride_id: int,
    user: requireSignin,
    session: GetSession,
    request: DefaultRideSettingForm = Depends(),
):
    user_id = user.get("id")

    # ------------------------------
    #  Find DefaultRideSetting and Verify Owner
    # ------------------------------
    ride = session.get(DefaultRideSetting, ride_id)

    if not ride:
        return api_response(404, "DefaultRideSetting not found")

    if ride.user_id != user_id:
        return api_response(403, "You are not allowed to update this ride")

    # ------------------------------
    #  Handle new car_pic upload
    # ------------------------------

    if request.car_pic:
        files = [request.car_pic]
        saved_files = await uploadImage(files, thumbnail=False)
        records = entryMedia(session, saved_files)

        request.car_pic = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )

    # ------------------------------
    #  Convert to serializable dict
    # ------------------------------

    # delete_files = json.loads(request.delete_images)
    update_data = updateOp(ride, request, session)
    ride_data = serialize_obj(update_data)

    if request.delete_images:
        delete_files = parse_list(request.delete_images)
        delete_images = []

        # -------------------------
        #  CAR PIC DELETE
        # -------------------------
        car_pic = ride_data.get("car_pic")  # dict or None

        if car_pic:
            car_pic_filename = car_pic.get("filename")

            if car_pic_filename and car_pic_filename in delete_files:
                delete_images.append(car_pic_filename)

                # remove from update_data (Ride ORM)
                update_data.car_pic = None

        delete_media_items(session, filenames=delete_images)

    session.commit()
    session.refresh(update_data)

    # ------------------------------
    # Return formatted response
    # ------------------------------
    return api_response(200, "Ride Updated Successfully", update_data)


@router.get("/read", response_model=DefaultRideSettingRead)
def findOne(
    user: requireSignin,
    session: GetSession,
):
    user_id = user.get("id")

    read = session.exec(
        select(DefaultRideSetting).where(DefaultRideSetting.user_id == user_id)
    ).first()

    raiseExceptions((read, 404, "Ride not found"))
    data = DefaultRideSetting.model_validate(read)
    return api_response(200, "Ride Found", data)
