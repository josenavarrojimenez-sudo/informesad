/**
 * BACKEND SYNC - Expedientes CDV
 * 
 * INSTRUCCIONES:
 * 1. Abrí Google Sheets (el mismo de siempre)
 * 2. Extensiones → Apps Script → reemplazá todo con este código
 * 3. Guardá → Implementar → Administrar implementaciones → editar → Nueva versión → Implementar
 * 4. URL del backend: https://script.google.com/macros/s/AKfycbw6WJK2KZr79e6AjfbN4BCX1n1JSsymuvAiniFO6nE_fnMD7d5D5gtGoIx53Prs44vwhA/exec
 */

const SECRET_TOKEN = "Adelante2025";
const SHEET_NAME = "EXPEDIENTES_DB";

/**
 * GET: ?expedienteId=K.18
 * Returns the saved data for that expediente, or empty if not found.
 */
function doGet(e) {
  try {
    const expedienteId = e.parameter && e.parameter.expedienteId;
    const sheet = getOrCreateSheet();
    const data = sheet.getDataRange().getValues();

    if (data.length <= 1) {
      return response({ status: "ok", data: null });
    }

    const rows = data.slice(1); // skip header
    if (expedienteId) {
      // Return specific expediente
      const row = rows.find(r => r[0] === expedienteId);
      if (!row) return response({ status: "ok", data: null });
      return response({ status: "ok", data: JSON.parse(row[1]) });
    } else {
      // Return all expedientes (list of IDs)
      const ids = rows.map(r => r[0]).filter(Boolean);
      return response({ status: "ok", expedientes: ids });
    }
  } catch (err) {
    return response({ status: "error", message: err.toString() });
  }
}

/**
 * POST: { token, expedienteId, data }
 * Saves/updates the data for that expediente.
 * data.files is excluded to avoid quota issues (files stay in localStorage only).
 */
function doPost(e) {
  try {
    const params = JSON.parse(e.postData.contents);

    if (params.token !== SECRET_TOKEN) {
      return response({ status: "error", message: "Token inválido" });
    }

    const expedienteId = params.expedienteId;
    if (!expedienteId) {
      return response({ status: "error", message: "Falta expedienteId" });
    }

    // Strip files (too large for Sheets, keep only statuses)
    const saveData = {
      statuses: params.data ? params.data.statuses : {},
      updatedAt: new Date().toISOString()
    };

    const sheet = getOrCreateSheet();
    const data = sheet.getDataRange().getValues();
    const rows = data.slice(1);

    // Find existing row
    let found = false;
    for (let i = 0; i < rows.length; i++) {
      if (rows[i][0] === expedienteId) {
        sheet.getRange(i + 2, 2).setValue(JSON.stringify(saveData));
        found = true;
        break;
      }
    }

    if (!found) {
      sheet.appendRow([expedienteId, JSON.stringify(saveData)]);
    }

    return response({ status: "ok", message: "Guardado: " + expedienteId });
  } catch (err) {
    return response({ status: "error", message: err.toString() });
  }
}

function getOrCreateSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["EXPEDIENTE_ID", "JSON_DATA"]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function response(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
