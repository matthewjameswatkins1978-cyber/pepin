#include "abi_fixture_types.h"

#include <stdio.h>

static const char *fixture_compiler(void) {
#if defined(__clang__)
    return "clang";
#elif defined(__GNUC__)
    return "gcc";
#else
    return "unknown";
#endif
}

static int valid_layout(const pep_fixture_report *report) {
    return report->point_y_offset == sizeof(int64_t) &&
        report->point_size >= 2 * sizeof(int64_t) &&
        report->point_align >= _Alignof(int64_t) &&
        report->tree_payload_offset >= sizeof(pep_fixture_tree_tag) &&
        report->tree_size >= report->tree_payload_offset + sizeof(void *) * 2 &&
        report->tree_align >= _Alignof(void *);
}

int main(void) {
    pep_fixture_report report = { 0 };
    pep_status status = pep_abi_fixture_run(&report);
    if (status != PEP_OK) {
        fprintf(stderr, "ABI_ERROR|status=%s\n", pep_status_name(status));
        return 2;
    }
    if (!valid_layout(&report) || report.point_sum != 42 || report.tree_sum != 42 ||
        report.list_sum != 49 || report.utf8_len != 3 ||
        report.overflow_status != PEP_ERR_OVERFLOW ||
        report.invalid_tag_status != PEP_ERR_INVALID_VARIANT ||
        report.owner_mismatch_status != PEP_ERR_RANGE ||
        report.owner_recovery_status != PEP_OK) {
        fprintf(stderr, "ABI_ERROR|semantic_or_layout_mismatch\n");
        return 3;
    }
    printf("ABI|compiler=%s|status=ok|point_sum=%lld|tree_sum=%lld|list_sum=%lld|utf8_len=%zu\n",
           fixture_compiler(), (long long)report.point_sum, (long long)report.tree_sum,
           (long long)report.list_sum, report.utf8_len);
    printf("LAYOUT|point_size=%zu|point_align=%zu|point_y_offset=%zu|tree_size=%zu|tree_align=%zu|tree_payload_offset=%zu\n",
           report.point_size, report.point_align, report.point_y_offset,
           report.tree_size, report.tree_align, report.tree_payload_offset);
    printf("ERRORS|overflow=%s|invalid_tag=%s|owner_mismatch=%s|owner_recovery=%s\n",
           pep_status_name(report.overflow_status), pep_status_name(report.invalid_tag_status),
           pep_status_name(report.owner_mismatch_status), pep_status_name(report.owner_recovery_status));
    return 0;
}
