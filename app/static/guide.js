(function () {
    "use strict";

    var steps = [
        {
            target: '[data-guide="navigation"]',
            title: "Votre espace de veille",
            text: "Retrouvez ici le dashboard, la capture, vos sources et vos republications."
        },
        {
            target: '[data-guide="capture-link"]',
            title: "Capturer une idee",
            text: "Ajoutez une URL ou une note pour alimenter votre base de veille."
        },
        {
            target: '[data-guide="sources-link"]',
            title: "Suivre vos sources",
            text: "Ouvrez une fiche pour qualifier, ranger et digerer chaque source."
        },
        {
            target: '[data-guide="dashboard"]',
            title: "Votre tableau de bord",
            text: "Le dashboard vous donne un point de depart simple vers les actions principales."
        },
        {
            target: '[data-guide="workspace"]',
            title: "Faire avancer une source",
            text: "Dans chaque fiche, les sections vous accompagnent de la qualification a la digestion."
        },
        {
            target: '[data-guide="republications-link"]',
            title: "Preparer une republication",
            text: "Retrouvez vos brouillons et vos publications depuis cet espace dedie."
        }
    ];

    var currentStep = 0;
    var overlay;
    var dialog;
    var spotlight;

    function findTarget(step) {
        return document.querySelector(step.target) || document.querySelector('[data-guide="workspace"]');
    }

    function closeGuide() {
        if (!overlay) {
            return;
        }
        overlay.remove();
        overlay = null;
        dialog = null;
        spotlight = null;
        document.body.classList.remove("guide-ouvert");
    }

    function renderStep() {
        var step = steps[currentStep];
        var target = findTarget(step);
        var bounds = target.getBoundingClientRect();
        var padding = 8;

        spotlight.style.top = Math.max(8, bounds.top - padding) + "px";
        spotlight.style.left = Math.max(8, bounds.left - padding) + "px";
        spotlight.style.width = bounds.width + padding * 2 + "px";
        spotlight.style.height = bounds.height + padding * 2 + "px";
        dialog.querySelector("[data-guide-title]").textContent = step.title;
        dialog.querySelector("[data-guide-text]").textContent = step.text;
        dialog.querySelector("[data-guide-count]").textContent = "Etape " + (currentStep + 1) + " / " + steps.length;
        dialog.querySelector("[data-guide-previous]").disabled = currentStep === 0;
        dialog.querySelector("[data-guide-next]").textContent = currentStep === steps.length - 1 ? "Terminer" : "Suivant";

        var dialogTop = bounds.bottom + 18;
        if (dialogTop + dialog.offsetHeight > window.innerHeight - 16) {
            dialogTop = Math.max(16, bounds.top - dialog.offsetHeight - 18);
        }
        dialog.style.top = dialogTop + "px";
        dialog.style.left = Math.min(Math.max(16, bounds.left), window.innerWidth - dialog.offsetWidth - 16) + "px";
    }

    function openGuide() {
        if (overlay) {
            return;
        }
        currentStep = 0;
        overlay = document.createElement("div");
        overlay.className = "guide-overlay";
        overlay.innerHTML =
            '<div class="guide-spotlight" aria-hidden="true"></div>' +
            '<section class="guide-dialog" role="dialog" aria-modal="true" aria-labelledby="guide-title">' +
                '<button class="guide-close" type="button" aria-label="Fermer le guide">&times;</button>' +
                '<p class="guide-count" data-guide-count></p>' +
                '<h2 id="guide-title" data-guide-title></h2>' +
                '<p data-guide-text></p>' +
                '<div class="guide-actions">' +
                    '<button class="bouton bouton-secondaire" type="button" data-guide-previous>Precedent</button>' +
                    '<button class="bouton" type="button" data-guide-next>Suivant</button>' +
                '</div>' +
            '</section>';
        document.body.appendChild(overlay);
        spotlight = overlay.querySelector(".guide-spotlight");
        dialog = overlay.querySelector(".guide-dialog");
        document.body.classList.add("guide-ouvert");

        overlay.addEventListener("click", function (event) {
            if (event.target === overlay || event.target.closest(".guide-close")) {
                closeGuide();
            } else if (event.target.matches("[data-guide-previous]")) {
                currentStep = Math.max(0, currentStep - 1);
                renderStep();
            } else if (event.target.matches("[data-guide-next]")) {
                if (currentStep === steps.length - 1) {
                    closeGuide();
                } else {
                    currentStep += 1;
                    renderStep();
                }
            }
        });

        renderStep();
        dialog.querySelector(".guide-close").focus();
    }

    document.addEventListener("DOMContentLoaded", function () {
        var startButton = document.querySelector("[data-guide-start]");
        if (!startButton) {
            return;
        }
        startButton.addEventListener("click", openGuide);
        window.addEventListener("resize", function () {
            if (overlay) {
                renderStep();
            }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && overlay) {
                closeGuide();
            }
        });
    });
})();
