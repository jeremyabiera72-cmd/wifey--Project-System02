/*
 * Fare estimate shared by the booking and edit-booking forms.
 *
 * Every vehicle type is priced the same way, from data attributes that
 * app.py put on the <option> straight from its vehicle_types row:
 *
 *   trip fare  = max(min fare, base fare + max(0, km - included km) * rate)
 *   total fare = trip fare x passengers   (per_passenger)
 *              = trip fare                (per_booking)
 *              + additional charges
 *
 * get_fare_breakdown() in app.py runs the same formula server-side, and the
 * fare that gets saved is always the server's, never this one.
 */

function readFareSettings(selected) {
    function number(attribute) {
        const value = parseFloat(selected.getAttribute(attribute));
        return isNaN(value) ? 0 : value;
    }

    return {
        baseFare: number("data-base-fare"),
        includedDistance: number("data-included-distance"),
        ratePerKm: number("data-rate-per-km"),
        minFare: number("data-min-fare"),
        extraCharges: number("data-extra-charges"),
        extraChargesLabel: selected.getAttribute("data-extra-label") || "fees",
        chargeBasis: selected.getAttribute("data-charge-basis") || "per_booking"
    };
}

function calculateFare(settings, km, passengers) {
    const extraDistance = Math.max(0, km - settings.includedDistance);
    const distanceCharge = extraDistance * settings.ratePerKm;
    const meteredFare = settings.baseFare + distanceCharge;
    const tripFare = Math.max(settings.minFare, meteredFare);
    const times = settings.chargeBasis === "per_passenger" ? passengers : 1;

    return {
        extraDistance: extraDistance,
        distanceCharge: distanceCharge,
        tripFare: tripFare,
        minimumFareApplied: settings.minFare > meteredFare,
        subtotal: tripFare * times,
        total: tripFare * times + settings.extraCharges
    };
}

function fareMoney(value) {
    return "\u20B1" + value.toFixed(2);
}

/* Kilometres are shown with the same 2 decimals the server prices with, so the
   printed lines multiply out to the printed total. */
function fareKm(value) {
    return String(Math.round(value * 100) / 100);
}

function fareLine(label, value, isTotal) {
    return '<div class="fb-row' + (isTotal ? " fb-total" : "") + '">' +
        "<span>" + label + "</span><span>" + value + "</span></div>";
}

function fareBreakdownLines(settings, km, passengers) {
    const result = calculateFare(settings, km, passengers);
    const perPassenger = settings.chargeBasis === "per_passenger";
    const lines = [fareLine("Route distance", fareKm(km) + " km")];

    if (settings.baseFare) {
        const label = settings.includedDistance
            ? "Base fare (first " + fareKm(settings.includedDistance) + " km)"
            : "Base fare";
        lines.push(fareLine(label, fareMoney(settings.baseFare)));
    }

    if (result.extraDistance > 0 && settings.ratePerKm) {
        const start = settings.baseFare
            ? " after " + fareKm(settings.includedDistance) + " km"
            : "";
        lines.push(fareLine(
            fareKm(result.extraDistance) + " km" + start + " x " +
            fareMoney(settings.ratePerKm) + "/km",
            fareMoney(result.distanceCharge)
        ));
    }

    if (result.minimumFareApplied) {
        lines.push(fareLine(
            "Minimum fare " + fareMoney(settings.minFare),
            fareMoney(result.tripFare)
        ));
    }

    if (perPassenger && passengers > 1) {
        lines.push(fareLine(
            fareMoney(result.tripFare) + " x " + passengers + " passenger(s)",
            fareMoney(result.subtotal)
        ));
    }

    if (settings.extraCharges) {
        lines.push(fareLine(
            settings.extraChargesLabel,
            fareMoney(settings.extraCharges)
        ));
    }

    lines.push(fareLine(
        perPassenger ? "Estimated total" : "Estimated total for the booking",
        fareMoney(result.total),
        true
    ));

    if (!perPassenger && passengers > 1) {
        lines.push(fareLine(
            "Shown per ticket (" + passengers + " passengers)",
            fareMoney(result.total / passengers)
        ));
    }

    return lines;
}

function updateFare() {
    const vehicle = document.getElementById("vehicle");
    const distance = document.getElementById("distance");
    const passengers = document.getElementById("passengers");
    const fare = document.getElementById("fare");
    const breakdownBox = document.getElementById("fare-breakdown");

    if (!vehicle || !distance || !passengers || !fare) {
        return;
    }

    function show(total, lines) {
        fare.textContent = fareMoney(total);
        if (breakdownBox) {
            breakdownBox.innerHTML = lines.join("");
        }
    }

    const selected = vehicle.options[vehicle.selectedIndex];

    if (!selected || !selected.value) {
        show(0, []);
        return;
    }

    const settings = readFareSettings(selected);
    const km = parseFloat(distance.value) || 0;
    const numberOfPassengers = Math.max(1, parseInt(passengers.value, 10) || 1);

    if (km <= 0) {
        show(0, [fareLine("Select pickup and destination to see the fare.", "\u2014")]);
        return;
    }

    show(calculateFare(settings, km, numberOfPassengers).total,
         fareBreakdownLines(settings, km, numberOfPassengers));
}
