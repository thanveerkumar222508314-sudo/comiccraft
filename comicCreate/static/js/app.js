document.addEventListener(
    "DOMContentLoaded",
    function () {

        const form =
            document.getElementById(
                "comic-form"
            );


        const button =
            document.getElementById(
                "generate-btn"
            );


        if (!form || !button) {
            return;
        }


        form.addEventListener(
            "submit",
            function () {

                button.disabled = true;

                button.innerHTML =
                    "⏳ Creating your comic...";

                button.style.opacity =
                    "0.7";

            }
        );

    }
);