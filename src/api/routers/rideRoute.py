from datetime import datetime, timezone
import json
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, File
from fastapi import UploadFile as UploadFileType
from sqlmodel import select
from starlette.datastructures import UploadFile
from fastapi.encoders import jsonable_encoder
from src.api.models.mediaModel import Media
from src.api.core.dependencies import ListQueryParams
from src.api.core.response import raiseExceptions
from src.api.core.utility import (
    parse_date,
    parse_list,
)
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.operation.media import delete_media_items, entryMedia, uploadImage
from src.api.models.rideModel import Ride, RideRead, RideReadWithUser, UserRideForm
from src.api.core import (
    GetSession,
    api_response,
    requireSignin,
    requireAdmin,
    requirePermission,
    verifiedUser,
)

router = APIRouter(prefix="/ride", tags=["ride"])


@router.post("/create", response_model=RideRead)
async def create_ride(
    user: requireSignin,
    session: GetSession,
    request: UserRideForm = Depends(),
):
    user_id = user.get("id")
    print("==================>", type(request.car_pic))
    print("====================>", request.car_pic)
    # print("request====================", request.other_images)
    if isinstance(request.car_pic, UploadFile):
        files = [request.car_pic]
        saved_files = await uploadImage(files, thumbnail=False)

        records = entryMedia(session, saved_files)

        request.car_pic = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )

    if isinstance(request.car_pic, str):  # URL should be string, not URL type
        statement = select(Media).where(Media.filename == request.car_pic)
        media = session.exec(statement).first()

        if media:
            request.car_pic = media.model_dump(
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

    # Add user_id
    ride_data = serialize_obj(request)
    ride_data["user_id"] = user_id

    # print("ride_data==================", ride_data)
    if "arrival_time" in ride_data:
        ride_data["arrival_time"] = parse_date(ride_data["arrival_time"])

    # Create Ride instance
    ride = Ride(**ride_data)
    session.add(ride)
    session.commit()
    session.refresh(ride)
    print("typeof", type(ride))
    # ride_json = jsonable_encoder(RideRead.model_validate(ride))
    return api_response(200, "Ride Create Successfully", ride)


@router.put("/update/{ride_id}", response_model=RideRead)
async def update_ride(
    ride_id: int,
    user: verifiedUser,
    session: GetSession,
    request: UserRideForm = Depends(),
):

    user_id = user.get("id")

    # ------------------------------
    #  Find Ride and Verify Owner
    # ------------------------------
    ride = session.get(Ride, ride_id)

    if not ride:
        return api_response(404, "Ride not found")

    if ride.user_id != user_id:
        return api_response(403, "You are not allowed to update this ride")

    # ------------------------------
    #  Convert from_ → from_location
    # ------------------------------
    if request.from_:
        request.from_location = {
            "type": "Point",
            "coordinates": [
                float(request.from_["longitude"]),
                float(request.from_["latitude"]),
            ],
        }

    # ------------------------------
    #  Convert to_ → to_location
    # ------------------------------
    if request.to_:
        request.to_location = {
            "type": "Point",
            "coordinates": [
                float(request.to_["longitude"]),
                float(request.to_["latitude"]),
            ],
        }

    print("=========================", request.__dict__)

    # ------------------------------
    #  Handle new car_pic upload
    # ------------------------------
    if isinstance(request.car_pic, UploadFile):
        if ride.car_pic:
            delete_media_items(session, filenames=[ride.car_pic["filename"]])

        files = [request.car_pic]
        saved_files = await uploadImage(files, thumbnail=False)
        records = entryMedia(session, saved_files)

        request.car_pic = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )
    else:
        # Not a file → do NOT update
        if hasattr(request, "car_pic"):
            delattr(request, "car_pic")

    # ------------------------------
    #  Handle new other_images upload
    # ------------------------------

    existing_images = ride.other_images or []
    new_uploaded_images = []
    filenames_to_delete = []

    # -----------------------
    # 1️⃣ DELETE REQUESTED IMAGES
    # -----------------------
    if request.delete_images:
        filenames_to_delete = request.delete_images

        # Remove from existing_images
        existing_images = [
            img
            for img in existing_images
            if img.get("filename") not in filenames_to_delete
        ]

        # Delete from media table
        delete_media_items(session, filenames=filenames_to_delete)

    # -----------------------
    # 2️⃣ HANDLE NEW UPLOADS
    # -----------------------
    if hasattr(request, "other_images"):
        upload_files = [f for f in request.other_images if isinstance(f, UploadFile)]

        if upload_files:
            saved_files = await uploadImage(upload_files, thumbnail=False)
            records = entryMedia(session, saved_files)

            new_uploaded_images = [
                r.model_dump(include={"id", "filename", "original", "media_type"})
                for r in records
            ]

    # -----------------------
    # 3️⃣ MERGE EXISTING + NEW
    # -----------------------
    merged_images = existing_images + new_uploaded_images
    request.other_images = merged_images

    # ------------------------------
    #  Convert to serializable dict
    # ------------------------------

    # delete_files = json.loads(request.delete_images)
    update_data = updateOp(ride, request, session)

    # ------------------------------
    # Convert arrival_time string → datetime
    # ------------------------------
    if "arrival_time" in update_data and update_data["arrival_time"]:
        update_data["arrival_time"] = parse_date(update_data["arrival_time"])

    session.commit()
    session.refresh(update_data)

    # ------------------------------
    # Return formatted response
    # ------------------------------
    return api_response(200, "Ride Updated Successfully", update_data)


@router.get("/read/{id}", response_model=RideReadWithUser)
def findOne(
    id: int,
    session: GetSession,
):

    read = session.get(Ride, id)  # Like findById

    raiseExceptions((read, 404, "Ride not found"))
    data = RideReadWithUser.model_validate(read)
    # 👇 condition here
    if not data.user or not data.user.verified:
        return api_response(400, "User Not Verified")

    return api_response(200, "Ride Found", data)


@router.get("/list", response_model=list[RideRead])
def list(query_params: ListQueryParams, session: GetSession):
    query_params = vars(query_params)
    searchFields = [
        "from_address",
        "to_address",
        "car_number",
        "car_type",
        "car_name",
        "car_model",
    ]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Ride,
        Schema=RideRead,
    )


@router.get("/listbyuserid", response_model=List[RideRead])
def list(query_params: ListQueryParams, user: requireSignin, session: GetSession):
    query_params = vars(query_params)
    searchFields = [
        "from_address",
        "to_address",
        "car_number",
        "car_type",
        "car_name",
        "car_model",
    ]
    user_id = user.get("id")
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Ride,
        Schema=RideRead,
        customFilters=[["user_id", user_id]],
    )


@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user: requireSignin,
):
    user_id = user.get("id")

    ride = session.get(Ride, id)

    raiseExceptions((ride, 404, "Ride Data not found"))
    if ride.user_id != user_id:
        return api_response(403, "You are not allowed to update this ride")

    filenames_to_delete = []
    # -------------------------
    # CAR PIC
    # -------------------------
    if ride.car_pic and isinstance(ride.car_pic, dict):
        filename = ride.car_pic.get("filename")
        if filename:
            filenames_to_delete.append(filename)

    # -------------------------
    # OTHER IMAGES
    # -------------------------
    if isinstance(ride.other_images, List) and ride.other_images:
        for img in ride.other_images:
            if isinstance(img, dict) and img.get("filename"):
                filenames_to_delete.append(img["filename"])

    # -------------------------
    # DELETE MEDIA FILES
    # -------------------------
    if filenames_to_delete:
        delete_media_items(session, filenames=filenames_to_delete)

    session.delete(ride)
    session.commit()
    return api_response(200, f"Ride {ride.id} deleted")
