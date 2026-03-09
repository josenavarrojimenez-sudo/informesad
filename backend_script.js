/**
 * BACKEND UNIFICADO - Ciudad del Valle
 * Maneja:
 *   1. type=casa_edits          → ediciones del informe principal
 *   2. expedienteId=X           → estados de requisitos por lote (update.html)
 *   3. action=save&expedienteId → guardar expediente vía GET (evita CORS)
 *   4. action=send_code         → envía código OTP al correo autorizado
 *   5. action=verify_code       → verifica código OTP
 */

const SECRET_TOKEN = "Adelante2025";
const SHEET_EXPEDIENTES = "EXPEDIENTES_DB";
const SHEET_CASAS = "CASAS_DB";
const SHEET_AUTH = "AUTH_CODES";

const AUTHORIZED_EMAILS = [
  "j@adelante.cr",
  "willem@adelantedesarrollos.com",
  "luiscarlos@adelantedesarrollos.com",
  "hazel@adelantedesarrollos.com",
  "luisroberto@adelante.cr",
  "daniel@adelante.cr",
  "david@adelante.cr"
];

const CODE_EXPIRY_MS = 10 * 60 * 1000; // 10 minutos

function doGet(e) {
  try {
    const p = e.parameter || {};
    const action = p.action;
    const type = p.type;
    const expedienteId = p.expedienteId;

    // ── AUTH: enviar código OTP ──────────────────────────────────────────────
    if (action === 'send_code') {
      const email = (p.email || '').toLowerCase().trim();
      if (!AUTHORIZED_EMAILS.includes(email)) {
        return response({ status: "error", message: "Correo no autorizado." });
      }
      const code = Math.floor(100000 + Math.random() * 900000).toString();
      const expiry = new Date(Date.now() + CODE_EXPIRY_MS).toISOString();

      // Guardar código en hoja
      const sheet = getOrCreateSheet(SHEET_AUTH, ["EMAIL", "CODE", "EXPIRY", "USED"]);
      // Limpiar códigos viejos del mismo correo
      const data = sheet.getDataRange().getValues();
      for (let i = data.length - 1; i >= 1; i--) {
        if (data[i][0] === email) sheet.deleteRow(i + 1);
      }
      sheet.appendRow([email, code, expiry, "false"]);

      // Enviar email
      MailApp.sendEmail({
        to: email,
        subject: "🔐 Código de acceso — CDV Formalización",
        body: `Hola,\n\nTu código de acceso al informe Ciudad del Valle es:\n\n    ${code}\n\nVálido por 10 minutos.\n\nSi no solicitaste este código, ignorá este mensaje.\n\n— Sistema CDV Adelante`
      });

      return response({ status: "ok", message: "Código enviado." });
    }

    // ── AUTH: verificar código OTP ───────────────────────────────────────────
    if (action === 'verify_code') {
      const email = (p.email || '').toLowerCase().trim();
      const code = (p.code || '').trim();

      const sheet = getOrCreateSheet(SHEET_AUTH, ["EMAIL", "CODE", "EXPIRY", "USED"]);
      const data = sheet.getDataRange().getValues();
      const rows = data.slice(1);

      for (let i = 0; i < rows.length; i++) {
        const [rowEmail, rowCode, rowExpiry, rowUsed] = rows[i];
        if (rowEmail === email && rowCode === code && rowUsed === "false") {
          if (new Date() > new Date(rowExpiry)) {
            return response({ status: "error", message: "Código expirado." });
          }
          // Marcar como usado
          sheet.getRange(i + 2, 4).setValue("true");
          return response({ status: "ok", email: email });
        }
      }
      return response({ status: "error", message: "Código incorrecto." });
    }

    // ── SAVE expediente via GET ──────────────────────────────────────────────
    if (action === 'save') {
      if (p.token !== SECRET_TOKEN) return response({ status: "error", message: "Token inválido" });
      if (!expedienteId) return response({ status: "error", message: "Falta expedienteId" });
      const incoming = p.data ? JSON.parse(p.data) : {};
      const saveData = { statuses: incoming.statuses || {}, updatedAt: new Date().toISOString() };
      const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
      const data = sheet.getDataRange().getValues();
      const rows = data.slice(1);
      let found = false;
      for (let i = 0; i < rows.length; i++) {
        if (rows[i][0] === expedienteId) { sheet.getRange(i + 2, 2).setValue(JSON.stringify(saveData)); found = true; break; }
      }
      if (!found) sheet.appendRow([expedienteId, JSON.stringify(saveData)]);
      return response({ status: "ok", message: "Expediente guardado: " + expedienteId });
    }

    // ── SAVE casas via GET ───────────────────────────────────────────────────
    if (action === 'save_casas') {
      if (p.token !== SECRET_TOKEN) return response({ status: "error", message: "Token inválido" });
      const incoming = p.data ? JSON.parse(p.data) : [];
      const sheet = getOrCreateSheet(SHEET_CASAS, ["JSON_DATA"]);
      sheet.clear();
      sheet.appendRow(["JSON_DATA"]);
      sheet.appendRow([JSON.stringify(incoming)]);
      return response({ status: "ok", message: "Casas guardadas" });
    }

    // ── READ casa_edits ──────────────────────────────────────────────────────
    if (type === 'casa_edits') {
      const sheet = getOrCreateSheet(SHEET_CASAS, ["JSON_DATA"]);
      const data = sheet.getDataRange().getValues();
      if (data.length <= 1) return response({ status: "ok", data: [] });
      const raw = data[1][0];
      return response({ status: "ok", data: raw ? JSON.parse(raw) : [] });
    }

    // ── READ expediente ──────────────────────────────────────────────────────
    if (expedienteId) {
      const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
      const data = sheet.getDataRange().getValues();
      if (data.length <= 1) return response({ status: "ok", data: null });
      const row = data.slice(1).find(r => r[0] === expedienteId);
      if (!row) return response({ status: "ok", data: null });
      return response({ status: "ok", data: JSON.parse(row[1]) });
    }

    // ── LIST expedientes ─────────────────────────────────────────────────────
    const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
    const data = sheet.getDataRange().getValues();
    const ids = data.slice(1).map(r => r[0]).filter(Boolean);
    return response({ status: "ok", expedientes: ids });

  } catch (err) {
    return response({ status: "error", message: err.toString() });
  }
}

function doPost(e) {
  try {
    const params = JSON.parse(e.postData.contents);
    if (params.token !== SECRET_TOKEN) return response({ status: "error", message: "Token inválido" });
    if (params.type === 'casa_edits') {
      const sheet = getOrCreateSheet(SHEET_CASAS, ["JSON_DATA"]);
      sheet.clear(); sheet.appendRow(["JSON_DATA"]); sheet.appendRow([JSON.stringify(params.data || [])]);
      return response({ status: "ok", message: "Ediciones guardadas" });
    }
    const expedienteId = params.expedienteId;
    if (!expedienteId) return response({ status: "error", message: "Falta expedienteId" });
    const saveData = { statuses: params.data ? params.data.statuses : {}, updatedAt: new Date().toISOString() };
    const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
    const data = sheet.getDataRange().getValues();
    let found = false;
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === expedienteId) { sheet.getRange(i + 1, 2).setValue(JSON.stringify(saveData)); found = true; break; }
    }
    if (!found) sheet.appendRow([expedienteId, JSON.stringify(saveData)]);
    return response({ status: "ok", message: "Expediente guardado: " + expedienteId });
  } catch (err) {
    return response({ status: "error", message: err.toString() });
  }
}

function getOrCreateSheet(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) { sheet = ss.insertSheet(name); sheet.appendRow(headers); sheet.setFrozenRows(1); }
  return sheet;
}

function response(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
