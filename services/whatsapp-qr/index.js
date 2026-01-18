import express from "express";
import QRCode from "qrcode";
import pino from "pino";
import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import fs from "fs";
import path from "path";

const app = express();
app.use(express.json({ limit: "1mb" }));

const logger = pino({ level: process.env.LOG_LEVEL || "info" });
const dataDir = process.env.DATA_DIR || "/data";
const sessionsDir = path.join(dataDir, "sessions");

const sessions = new Map();

const ensureDir = (dirPath) => {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
};

ensureDir(sessionsDir);

const nowIso = () => new Date().toISOString();

const baseResponse = (entry) => ({
  gateway_id: entry.gatewayId,
  status: entry.status || "pending",
  qr_image_url: entry.qrImageUrl || "",
  message: entry.message || "",
  last_disconnect_reason: entry.lastDisconnectReason || null,
  last_disconnect_message: entry.lastDisconnectMessage || "",
  updated_at: entry.updatedAt || null,
});

const summarizeDisconnect = (lastDisconnect) => {
  const statusCode = lastDisconnect?.error?.output?.statusCode;
  const message =
    lastDisconnect?.error?.message ||
    lastDisconnect?.error?.output?.payload?.message ||
    lastDisconnect?.error?.output?.payload?.error ||
    "";
  return { statusCode: statusCode || null, message };
};

const createSession = async (gatewayId, name) => {
  const sessionPath = path.join(sessionsDir, String(gatewayId));
  ensureDir(sessionPath);

  const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
  const { version } = await fetchLatestBaileysVersion();

  const socket = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: "silent" }),
    printQRInTerminal: false,
    browser: ["ProveMaps", "Chrome", "1.0"],
    syncFullHistory: false,
  });

  socket.ev.on("creds.update", saveCreds);

  socket.ev.on("connection.update", async (update) => {
    const entry = sessions.get(gatewayId);
    if (!entry) {
      return;
    }
    logger.info(
      {
        gatewayId,
        connection: update.connection,
        hasQr: !!update.qr,
        lastDisconnect: summarizeDisconnect(update.lastDisconnect),
      },
      "connection.update"
    );

    if (update.qr) {
      try {
        entry.qrImageUrl = await QRCode.toDataURL(update.qr, {
          margin: 1,
          width: 280,
        });
        entry.status = "awaiting_qr";
        entry.message = "Aguardando leitura do QR.";
        entry.updatedAt = nowIso();
      } catch (error) {
        entry.status = "error";
        entry.message = "Falha ao gerar QR.";
        entry.updatedAt = nowIso();
      }
    }

    if (update.connection === "connecting") {
      entry.status = "connecting";
      entry.message = "Conectando...";
      entry.updatedAt = nowIso();
    }

    if (update.connection === "open") {
      entry.status = "connected";
      entry.qrImageUrl = "";
      entry.message = "Conectado.";
      entry.updatedAt = nowIso();
    }

    if (update.connection === "close") {
      const { statusCode, message } = summarizeDisconnect(update.lastDisconnect);
      const reasonCode = statusCode || "unknown";
      entry.lastDisconnectReason = reasonCode;
      entry.lastDisconnectMessage = message || "";
      entry.updatedAt = nowIso();

      if (reasonCode === DisconnectReason.restartRequired || reasonCode === 515 || reasonCode === "515") {
        entry.status = "connecting";
        entry.message = "Reconectando...";
        entry.socket = null;
        setTimeout(() => {
          ensureSession(gatewayId, entry.name).catch((error) => {
            logger.error({ error, gatewayId }, "Falha ao reiniciar sessão.");
          });
        }, 1000);
        return;
      }

      entry.status = "disconnected";
      entry.message = message
        ? `Desconectado (${reasonCode}): ${message}`
        : `Desconectado (${reasonCode}).`;

      if (reasonCode === DisconnectReason.loggedOut) {
        try {
          fs.rmSync(sessionPath, { recursive: true, force: true });
        } catch (error) {
          logger.warn({ gatewayId, error }, "Falha ao limpar sessão.");
        }
      }
    }
  });

  return socket;
};

const getOrCreateEntry = (gatewayId, name) => {
  const existing = sessions.get(gatewayId);
  if (existing && existing.socket) {
    return existing;
  }

  const entry = {
    gatewayId,
    name: name || `Gateway ${gatewayId}`,
    status: "pending",
    qrImageUrl: "",
    message: "Sessão inicializada.",
    updatedAt: nowIso(),
    socket: null,
  };
  sessions.set(gatewayId, entry);
  return entry;
};

const ensureSession = async (gatewayId, name) => {
  const entry = getOrCreateEntry(gatewayId, name);
  if (!entry.socket) {
    entry.status = "connecting";
    entry.message = "Iniciando sessão...";
    entry.updatedAt = nowIso();
    entry.socket = await createSession(gatewayId, name);
  }
  return entry;
};

const normalizeRecipient = (value) => {
  const raw = String(value || "").trim();
  if (!raw) return "";
  if (raw.includes("@")) return raw;
  const digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  return `${digits}@s.whatsapp.net`;
};

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

app.post("/qr/start", async (req, res) => {
  const gatewayId = String(req.body.gateway_id || "").trim();
  const name = req.body.name || "";

  if (!gatewayId) {
    return res.status(400).json({ success: false, message: "gateway_id é obrigatório." });
  }

  try {
    const entry = await ensureSession(gatewayId, name);
    logger.info({ gatewayId }, "QR start solicitado.");
    return res.json({ success: true, ...baseResponse(entry) });
  } catch (error) {
    logger.error({ error, gatewayId }, "Falha ao iniciar sessão.");
    return res.status(500).json({
      success: false,
      message: "Falha ao iniciar sessão.",
    });
  }
});

app.get("/qr/status", async (req, res) => {
  const gatewayId = String(req.query.gateway_id || "").trim();
  if (!gatewayId) {
    return res.status(400).json({ success: false, message: "gateway_id é obrigatório." });
  }

  const entry = sessions.get(gatewayId);
  if (!entry) {
    logger.info({ gatewayId }, "Status solicitado sem sessão.");
    return res.json({
      success: true,
      gateway_id: gatewayId,
      status: "pending",
      qr_image_url: "",
      message: "Sessão ainda não iniciada.",
      updated_at: null,
    });
  }

  logger.info({ gatewayId, status: entry.status }, "Status solicitado.");
  return res.json({ success: true, ...baseResponse(entry) });
});

app.post("/qr/disconnect", async (req, res) => {
  const gatewayId = String(req.body.gateway_id || "").trim();
  if (!gatewayId) {
    return res.status(400).json({ success: false, message: "gateway_id é obrigatório." });
  }

  const entry = sessions.get(gatewayId);
  if (!entry || !entry.socket) {
    logger.info({ gatewayId }, "Disconnect solicitado sem sessão.");
    return res.json({
      success: true,
      gateway_id: gatewayId,
      status: "disconnected",
      message: "Sessão já estava desconectada.",
      qr_image_url: "",
      updated_at: nowIso(),
    });
  }

  try {
    const sessionPath = path.join(sessionsDir, String(gatewayId));
    logger.info({ gatewayId }, "Disconnect solicitado.");
    await entry.socket.logout();
    entry.socket = null;
    entry.status = "disconnected";
    entry.qrImageUrl = "";
    entry.message = "Sessão desconectada.";
    entry.updatedAt = nowIso();
    sessions.delete(gatewayId);
    try {
      fs.rmSync(sessionPath, { recursive: true, force: true });
    } catch (error) {
      logger.warn({ gatewayId, error }, "Falha ao limpar sessão.");
    }
    return res.json({ success: true, ...baseResponse(entry) });
  } catch (error) {
    logger.error({ error, gatewayId }, "Falha ao desconectar sessão.");
    return res.status(500).json({ success: false, message: "Falha ao desconectar sessão." });
  }
});

app.post("/qr/reset", async (req, res) => {
  const gatewayId = String(req.body.gateway_id || "").trim();
  if (!gatewayId) {
    return res.status(400).json({ success: false, message: "gateway_id é obrigatório." });
  }

  const sessionPath = path.join(sessionsDir, String(gatewayId));
  const entry = sessions.get(gatewayId);
  if (entry?.socket) {
    try {
      await entry.socket.logout();
    } catch (error) {
      logger.warn({ gatewayId, error }, "Falha ao desconectar na limpeza.");
    }
  }

  sessions.delete(gatewayId);
  try {
    fs.rmSync(sessionPath, { recursive: true, force: true });
  } catch (error) {
    logger.warn({ gatewayId, error }, "Falha ao remover sessão.");
  }

  logger.info({ gatewayId }, "Sessão resetada.");
  return res.json({
    success: true,
    gateway_id: gatewayId,
    status: "reset",
    message: "Sessão limpa. Gere um novo QR.",
    qr_image_url: "",
    updated_at: nowIso(),
  });
});

app.post("/message/test", async (req, res) => {
  const gatewayId = String(req.body.gateway_id || "").trim();
  const recipient = normalizeRecipient(req.body.recipient);
  const message = String(req.body.message || "").trim();

  if (!gatewayId) {
    return res.status(400).json({ success: false, message: "gateway_id é obrigatório." });
  }
  if (!recipient) {
    return res.status(400).json({ success: false, message: "recipient é obrigatório." });
  }
  if (!message) {
    return res.status(400).json({ success: false, message: "message é obrigatório." });
  }

  const entry = sessions.get(gatewayId);
  if (!entry || !entry.socket) {
    return res.status(400).json({
      success: false,
      status: entry?.status || "pending",
      message: "Sessão ainda não foi iniciada.",
    });
  }
  if (entry.status !== "connected") {
    return res.status(400).json({
      success: false,
      status: entry.status,
      message: "Sessão não está conectada.",
    });
  }

  try {
    await entry.socket.sendMessage(recipient, { text: message });
    logger.info({ gatewayId, recipient }, "Mensagem de teste enviada.");
    return res.json({
      success: true,
      status: entry.status,
      message: "Mensagem enviada com sucesso.",
      recipient,
      updated_at: nowIso(),
    });
  } catch (error) {
    logger.error({ error, gatewayId }, "Falha ao enviar mensagem.");
    return res.status(500).json({
      success: false,
      status: entry.status,
      message: "Falha ao enviar mensagem.",
    });
  }
});

const port = Number(process.env.PORT || 3000);
app.listen(port, "0.0.0.0", () => {
  logger.info({ port }, "WhatsApp QR service iniciado.");
});
