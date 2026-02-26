/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { DynamicRecordList } from "@web/views/relational_model";
import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";

const AGGREGATABLE_FIELD_TYPES = ["float", "integer", "monetary"];
const formatters = registry.category("formatters");

/**
 * Patch DynamicRecordList to fetch server-side aggregates via read_group
 * when the list has more records than the visible page.
 */
patch(DynamicRecordList.prototype, "server_side_aggregates_model", {
    async _loadRecords() {
        const records = await this._super(...arguments);
        await this._fetchServerAggregates();
        return records;
    },

    async _fetchServerAggregates() {
        this._serverAggregates = null;

        // Only fetch server aggregates if paginated (more records than visible)
        if (this.count <= this.records.length) {
            return;
        }

        // Find fields that need aggregation (have sum/avg in the view AND group_operator in the model)
        const aggregateFields = [];
        for (const fieldName in this.activeFields) {
            const field = this.fields[fieldName];
            if (!field || !AGGREGATABLE_FIELD_TYPES.includes(field.type)) {
                continue;
            }
            if (!field.group_operator) {
                continue;
            }
            const rawAttrs = this.activeFields[fieldName].rawAttrs || {};
            if (rawAttrs.sum || rawAttrs.avg) {
                aggregateFields.push(fieldName);
            }
        }

        if (!aggregateFields.length) {
            return;
        }

        try {
            const result = await this.model.orm.readGroup(
                this.resModel,
                this.domain,
                aggregateFields,
                [],
                { context: this.context }
            );
            if (result && result.length) {
                this._serverAggregates = {};
                for (const fieldName of aggregateFields) {
                    if (fieldName in result[0]) {
                        this._serverAggregates[fieldName] = result[0][fieldName] || 0;
                    }
                }
            }
        } catch (e) {
            // Silently fail — fall back to client-side aggregation
            this._serverAggregates = null;
        }
    },
});

/**
 * Patch ListRenderer to use server-side aggregates when available
 * instead of computing from the visible page records.
 */
patch(ListRenderer.prototype, "server_side_aggregates_renderer", {
    get aggregates() {
        const list = this.props.list;

        // Use server aggregates only for ungrouped lists with no active selection
        if (
            !list.isGrouped &&
            !(list.selection && list.selection.length) &&
            list._serverAggregates
        ) {
            const aggregates = {};
            for (const fieldName in list.activeFields) {
                if (!(fieldName in list._serverAggregates)) {
                    continue;
                }
                const field = this.fields[fieldName];
                const { rawAttrs, widget } = list.activeFields[fieldName];
                const func =
                    (rawAttrs.sum && "sum") || (rawAttrs.avg && "avg");
                if (!func) {
                    continue;
                }
                const value = list._serverAggregates[fieldName];
                const type = field.type;
                const formatter = formatters.get(widget, false) || formatters.get(type, false);
                const formatOptions = {
                    digits: rawAttrs.digits ? JSON.parse(rawAttrs.digits) : undefined,
                    escape: true,
                };
                aggregates[fieldName] = {
                    help: rawAttrs[func],
                    value: formatter ? formatter(value, formatOptions) : value,
                };
            }
            return aggregates;
        }

        return this._super();
    },
});
