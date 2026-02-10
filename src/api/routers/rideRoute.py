from datetime import datetime, timezone
import json
from typing import List
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from src.api.core.dependencies import ListQueryParams
from src.api.core.response import raiseExceptions
from src.api.core.utility import (
    filter_upload_files,
    is_upload_file,
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
    print(type(request.other_images))
    print("request====================", request.other_images)
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
    #  Handle new car_pic upload
    # ------------------------------

    if request.car_pic and is_upload_file(request.car_pic):
        files = [request.car_pic]
        saved_files = await uploadImage(files, thumbnail=False)
        records = entryMedia(session, saved_files)

        request.car_pic = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )
    elif request.car_pic is None:
        # None → do not touch existing value
        delattr(request, "car_pic")

    # ------------------------------
    #  Handle new other_images upload
    # ------------------------------

    if request.other_images and len(request.other_images) > 0:
        upload_files = filter_upload_files(request.other_images)
        if upload_files:
            saved_files = await uploadImage(upload_files, thumbnail=False)
            records = entryMedia(session, saved_files)

            # Convert SQLModel objects to dict (safe for JSON)
            request.other_images = [
                r.model_dump(include={"id", "filename", "original", "media_type"})
                for r in records
            ]
    else:
        delattr(request, "other_images")

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

    # ------------------------------
    #  Convert to serializable dict
    # ------------------------------

    # delete_files = json.loads(request.delete_images)
    update_data = updateOp(ride, request, session)
    ride_data = serialize_obj(update_data)

    if request.delete_images and len(request.delete_images) > 0:
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

        # -------------------------
        # OTHER IMAGES DELETE
        # -------------------------
        # if not isinstance(ride_data.get("other_images"), list):
        #     other_imgs = ride_data.get("other_images") or []

        #     new_other_images = []  # rebuild list without deleted ones

        #     for img in other_imgs:
        #         filename = img.get("filename")

        #         if filename in delete_files:
        #             delete_images.append(filename)
        #             continue  # ← skip adding → removes from update_data

        #         new_other_images.append(img)

        #     # update ORM object
        #     update_data.other_images = new_other_images

        # delete_media_items(session, filenames=delete_images)

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
    query_params["customFilters"] = [["user_id", user_id]]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Ride,
        Schema=RideRead,
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

    session.delete(ride)
    session.commit()
    return api_response(404, f"Banner {ride.id} deleted")
