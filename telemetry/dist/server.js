"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const config_1 = require("./config");
const app_1 = require("./app");
const mongo_1 = require("./mongo");
const services_1 = require("./services");
async function main() {
    const config = (0, config_1.getConfig)();
    await (0, mongo_1.connectToMongo)(config);
    const userRepository = new mongo_1.MongoUserRepository();
    const telemetryRepository = new mongo_1.MongoTelemetryEventRepository();
    await (0, services_1.ensureAdminUser)(userRepository, config);
    const { app } = await (0, app_1.createApp)({
        config,
        telemetryRepository,
        userRepository,
    });
    const server = app.listen(config.port, () => {
        console.log(`BioNexus telemetry GraphQL service listening on port ${config.port}`);
    });
    const shutdown = async () => {
        await new Promise((resolve, reject) => {
            server.close((error) => {
                if (error) {
                    reject(error);
                    return;
                }
                resolve();
            });
        });
        await (0, mongo_1.disconnectFromMongo)();
    };
    process.on("SIGINT", () => {
        void shutdown().finally(() => process.exit(0));
    });
    process.on("SIGTERM", () => {
        void shutdown().finally(() => process.exit(0));
    });
}
void main().catch((error) => {
    console.error("Telemetry service failed to start", error);
    process.exit(1);
});
