(function () {
    "use strict";

    const form = document.getElementById("receipt-form");
    if (!form) return;

    const submitBtn = document.getElementById("receipt-submit");
    const resultBox = form.querySelector("[data-result]");

    const fieldConfig = {
        fn: { required: true, digits: true, label: "ФН" },
        fd: { required: true, digits: true, label: "ФД" },
        fp: { required: true, digits: true, label: "ФП" },
        purchased_at: { required: true, date: true },
        amount: { required: true, amount: true, minAmount: 1000 },
    };

    // Read minAmount from data attribute if provided
    const amountInput = form.elements["amount"];
    if (amountInput && amountInput.dataset.minAmount) {
        fieldConfig.amount.minAmount = parseFloat(amountInput.dataset.minAmount);
    }

    function clearErrors() {
        form.querySelectorAll(".form__error").forEach((el) => (el.textContent = ""));
        form.querySelectorAll("input").forEach((el) => el.classList.remove("is-invalid"));
        resultBox.hidden = true;
        resultBox.textContent = "";
        resultBox.classList.remove("form__result--success", "form__result--error");
    }

    function setFieldError(name, message) {
        const box = form.querySelector(`[data-error-for="${name}"]`);
        if (box) box.textContent = message;
        const input = form.elements[name];
        if (input) input.classList.add("is-invalid");
    }

  function validateClient() {
        const qrInput = form.elements["qr_string"];
        const qrFilled = qrInput && qrInput.value.trim().length > 0;
        const errors = {};
        const values = {};
        const photoInput = form.elements["photo"];
        if (photoInput && photoInput.files && photoInput.files.length > 0) {
            const f = photoInput.files[0];
            const maxBytes = 5 * 1024 * 1024;
            const minBytes = 10 * 1024;
            const allowed = ["image/jpeg", "image/png", "image/webp"];

            if (f.size > maxBytes) {
                errors.photo = `Файл больше ${maxBytes / (1024 * 1024)} МБ`;
            } else if (f.size < minBytes) {
                errors.photo = "Файл слишком маленький или повреждён";
            } else if (f.type && !allowed.includes(f.type)) {
                errors.photo = "Только JPEG, PNG или WEBP";
            }
        }

        for (const name of Object.keys(fieldConfig)) {
            const input = form.elements[name];
            if (!input) continue;
            values[name] = (input.value || "").trim();
        }

        if (qrFilled) {
            const requiredFields = ["fn", "fd", "fp", "purchased_at", "amount"];
            const allEmpty = requiredFields.every((n) => !values[n]);
            if (allEmpty) {
                return {};
            }
        }

        // fn / fd / fp
        for (const name of ["fn", "fd", "fp"]) {
            const cfg = fieldConfig[name];
            const v = values[name];
            if (!v) {
                errors[name] = "Обязательное поле";
            } else if (cfg.digits && !/^\d+$/.test(v)) {
                errors[name] = "Допустимы только цифры";
            }
        }

        // purchased_at
        if (!values.purchased_at) {
            errors.purchased_at = "Укажите дату и время покупки";
        } else {
            const dt = new Date(values.purchased_at);
            if (Number.isNaN(dt.getTime())) {
                errors.purchased_at = "Некорректная дата";
            } else {
                const input = form.elements.purchased_at;
                const min = input.dataset.dateMin;
                const max = input.dataset.dateMax;
                if (min && values.purchased_at.slice(0, 10) < min) {
                    errors.purchased_at = `Дата должна быть не раньше ${formatRu(min)}`;
                } else if (max && values.purchased_at.slice(0, 10) > max) {
                    errors.purchased_at = `Дата должна быть не позже ${formatRu(max)}`;
                }
            }
        }

        // amount
        if (!values.amount) {
            errors.amount = "Укажите сумму";
        } else {
            const num = Number(values.amount.replace(",", "."));
            if (!Number.isFinite(num) || num <= 0) {
                errors.amount = "Некорректная сумма";
            } else if (num < fieldConfig.amount.minAmount) {
                errors.amount = `Минимальная сумма — ${fieldConfig.amount.minAmount} ₽`;
            }
        }

        return errors;
    }

    function formatRu(iso) {
        const [y, m, d] = iso.split("-");
        return `${d}.${m}.${y}`;
    }

    function renderErrors(errors) {
        clearErrors();
        let hasError = false;
        for (const [name, msg] of Object.entries(errors)) {
            if (name === "__all__" || name === "non_field_errors") {
                resultBox.hidden = false;
                resultBox.classList.add("form__result--error");
                resultBox.textContent = Array.isArray(msg) ? msg.join(" ") : msg;
            } else {
                setFieldError(name, Array.isArray(msg) ? msg.join(" ") : msg);
            }
            hasError = true;
        }
        return hasError;
    }

    function parseQRString(raw) {
        if (!raw || typeof raw !== "string") return null;
        const trimmed = raw.trim();
        if (!trimmed) return null;

        const params = {};
        for (const pair of trimmed.split("&")) {
            const eq = pair.indexOf("=");
            if (eq < 0) continue;
            const key = pair.slice(0, eq).trim();
            const value = pair.slice(eq + 1).trim();
            if (key) params[key] = value;
        }

        const fn = params.fn;
        const fd = params.i;
        const fp = params.fp;
        const t = params.t;
        const s = params.s;
        if (!fn || !fd || !fp || !t || !s) return null;
        if (!/^\d+$/.test(fn) || !/^\d+$/.test(fd) || !/^\d+$/.test(fp)) return null;

        // t = 20261008T1200 | 20261008T120000 | 2026-10-08T12:00 | 2026-10-08T12:00:00
        const m = t.match(/^(\d{4})-?(\d{2})-?(\d{2})T(\d{2}):?(\d{2})(?::?(\d{2}))?$/);
        if (!m) return null;
        const [, y, mo, d, h, mi] = m;
        const purchasedAt = `${y}-${mo}-${d}T${h}:${mi}`;

        const amount = s.replace(",", ".");
        if (!/^\d+(\.\d+)?$/.test(amount)) return null;

        return { fn, fd, fp, purchased_at: purchasedAt, amount };
    }

    function fillFormFromQR() {
        const qrInput = form.elements["qr_string"];
        if (!qrInput) return false;

        const parsed = parseQRString(qrInput.value);
        if (!parsed) return false;

        const targets = {
            fn: parsed.fn,
            fd: parsed.fd,
            fp: parsed.fp,
            purchased_at: parsed.purchased_at,
            amount: parsed.amount,
        };

        let filled = false;
        for (const [name, value] of Object.entries(targets)) {
            const input = form.elements[name];
            if (!input) continue;
            if (!input.value.trim()) {
                input.value = value;
                filled = true;
            }
        }
        return filled;
    }

    const qrInput = form.elements["qr_string"];
    if (qrInput) {
        qrInput.addEventListener("blur", () => {
            fillFormFromQR();
        });
        qrInput.addEventListener("input", () => {
        });
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      fillFormFromQR();
      clearErrors();

        const clientErrors = validateClient();
        if (Object.keys(clientErrors).length > 0) {
            renderErrors(clientErrors);
            return;
        }

        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = "Отправляем…";

        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
                credentials: "same-origin",
            });

            const data = await response.json().catch(() => ({}));

            if (response.ok && data.ok) {
                clearErrors();
                resultBox.hidden = false;
                resultBox.classList.add("form__result--success");
                resultBox.textContent =
                    "Чек успешно зарегистрирован и отправлен на проверку. Сейчас перенаправим в личный кабинет…";
                setTimeout(() => {
                    window.location.href = data.redirect_url || "/receipts/";
                }, 1200);
                return;
            }

            const errors = data.errors || { __all__: ["Не удалось отправить форму"] };
            renderErrors(errors);
        } catch (err) {
            renderErrors({ __all__: ["Сеть недоступна. Попробуйте ещё раз."] });
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
})();
