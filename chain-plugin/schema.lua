local typedefs = require "kong.db.schema.typedefs"

return {
  name = "chain-plugin",
  fields = {
    { consumer = typedefs.no_consumer },
    { protocols = typedefs.protocols_http },
    { config = {
        type = "record",
        fields = {
          { chain = { type = "array", elements = { type = "string" }, required = true } },
          { log_path = { type = "string", required = false, default = "/var/log/microservices/audit.jsonl" } },
        },
        entity_checks = {
        }
      }
    }
  }
}
