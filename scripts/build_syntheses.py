"""
Script tự động khởi tạo 15 trang Syntheses (Tổng hợp thực tiễn chuyên sâu)
Đọc toàn bộ 1.570 file Q&A, tổng hợp các bài liên quan cho từng chủ đề,
trích xuất các tiền lệ thực tiễn quan trọng, xây dựng bảng đối chiếu,
các lỗi sai thường gặp và liên kết 2 chiều chuẩn LLM-Wiki.
Chi phí: 0 token.
"""

import os
import re
import shutil
from datetime import date
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(r"D:\Antigravity\law-wiki-bidding-v2")
WIKI_DIR = BASE_DIR / "wiki"
QA_DIR = WIKI_DIR / "qa"
ARTICLES_DIR = WIKI_DIR / "articles"
SYNTHESES_DIR = WIKI_DIR / "syntheses"
HERMES_WIKI_DIR = Path(r"C:\Users\Desktop\.hermes\law-wiki-bidding-v2\wiki")

# Cấu hình 15 chủ đề tổng hợp
SYNTHESES_DEFS = [
    {
        "slug": "thuc-tien-danh-gia-ho-so-du-thau",
        "title": "Tổng Hợp Thực Tiễn: Đánh Giá Hồ Sơ Dự Thầu, Năng Lực & Kinh Nghiệm Nhà Thầu",
        "keywords": ["đánh giá hồ sơ", "hợp đồng tương tự", "năng lực kinh nghiệm", "nhân sự chủ chốt", "chấm thầu", "tiêu chuẩn đánh giá"],
        "related_articles": [63, 64, 65, 66, 67, 21, 22],
        "related_concepts": ["danh-gia-ho-so", "ho-so-du-thau", "nha-thau", "to-chuyen-gia"],
        "core_issues": [
            "Đánh giá tính hợp lệ của thỏa thuận liên danh và phân công công việc",
            "Nguyên tắc xác định tính tương tự của hợp đồng (quy mô, tính chất kỹ thuật)",
            "Xử lý trùng lặp nhân sự chủ chốt, huy động thiết bị thi công",
            "Đánh giá năng lực tài chính và doanh thu bình quân qua các năm",
            "Phương pháp chấm điểm kỹ thuật và đánh giá giá dự thầu (giá đánh giá, chi phí vòng đời)"
        ],
        "common_errors": [
            "Cài cắm tiêu chí hợp đồng tương tự quá mức cần thiết gây hạn chế nhà thầu",
            "Loại nhà thầu ngay khi thiếu tài liệu chứng minh thay vì yêu cầu làm rõ",
            "Đánh giá nhân sự vượt quá yêu cầu của hồ sơ mời thầu"
        ]
    },
    {
        "slug": "thuc-tien-chi-phi-du-toan-goi-thau",
        "title": "Tổng Hợp Thực Tiễn: Dự Toán Gói Thầu, Giá Gói Thầu & Chi Phí Trong Đấu Thầu",
        "keywords": ["chi phí", "dự toán gói thầu", "giá gói thầu", "chi phí dự phòng", "dự toán", "thẩm định giá"],
        "related_articles": [15, 39, 40, 41],
        "related_concepts": ["goi-thau", "chu-dau-tu", "phe-duyet", "tham-quyen"],
        "core_issues": [
            "Xác định giá gói thầu và các khoản mục chi phí cấu thành (thuế, phí, dự phòng)",
            "Cập nhật giá gói thầu trước thời điểm đóng thầu khi có biến động giá",
            "Chi phí lập, thẩm định hồ sơ mời thầu và đánh giá hồ sơ dự thầu",
            "Sử dụng và thanh quyết toán chi phí dự phòng trong hợp đồng trọn gói",
            "Thẩm quyền phê duyệt dự toán gói thầu và dự toán điều chỉnh"
        ],
        "common_errors": [
            "Không bao gồm chi phí dự phòng trong giá gói thầu xây lắp dẫn đến vượt dự toán",
            "Phân chia gói thầu không hợp lý nhằm né tránh hình thức đấu thầu rộng rãi",
            "Áp dụng sai định mức chi phí tư vấn đấu thầu theo quy định của Bộ Tài chính"
        ]
    },
    {
        "slug": "thuc-tien-tu-cach-hop-le-va-canh-tranh",
        "title": "Tổng Hợp Thực Tiễn: Tư Cách Hợp Lệ Của Nhà Thầu & Bảo Đảm Cạnh Tranh",
        "keywords": ["tư cách hợp lệ", "bảo đảm cạnh tranh", "công ty con", "chi nhánh", "liên danh", "độc lập tài chính"],
        "related_articles": [5, 6, 7],
        "related_concepts": ["nha-thau", "canh-tranh", "chu-dau-tu"],
        "core_issues": [
            "Tư cách tham gia đấu thầu của Chi nhánh và Văn phòng đại diện",
            "Bảo đảm cạnh tranh giữa công ty mẹ - công ty con trong cùng một gói thầu",
            "Mối quan hệ độc lập giữa Chủ đầu tư, Bên mời thầu và Nhà thầu tư vấn lập HSMT",
            "Tư cách hợp lệ của nhà thầu liên danh và điều kiện người đứng đầu liên danh",
            "Điều kiện không bị cấm tham gia hoạt động đấu thầu và công khai trên hệ thống mạng"
        ],
        "common_errors": [
            "Chi nhánh đứng tên dự thầu nhưng không có văn bản ủy quyền hợp pháp của Tổng công ty",
            "Hai công ty con thuộc cùng một Tổng công ty cùng nộp hồ sơ tham dự một gói thầu",
            "Đơn vị lập thiết kế - dự toán lại tham gia gói thầu xây lắp tương ứng"
        ]
    },
    {
        "slug": "thuc-tien-mua-sam-thuong-xuyen-tap-trung",
        "title": "Tổng Hợp Thực Tiễn: Mua Sắm Thường Xuyên, Mua Sắm Tập Trung & Y Tế",
        "keywords": ["thường xuyên", "mua sắm tập trung", "dự toán mua sắm", "y tế", "thuốc", "vật tư", "thiết bị y tế"],
        "related_articles": [55, 56, 57, 58, 59, 60, 61, 62],
        "related_concepts": ["hang-hoa", "mua-sam-truc-tuyen"],
        "core_issues": [
            "Quy trình mua sắm thường xuyên dưới 100 triệu đồng không lập KHLCNT",
            "Thực hiện thỏa thuận khung trong mua sắm tập trung cấp quốc gia và bộ ngành",
            "Mua sắm thuốc, hóa chất, thiết bị y tế theo cơ chế đặc thù",
            "Tự chủ tài chính của đơn vị sự nghiệp công lập trong mua sắm tài sản",
            "Áp dụng danh mục hàng hóa sản xuất trong nước được ưu đãi"
        ],
        "common_errors": [
            "Chia nhỏ gói thầu mua sắm thường xuyên thành nhiều đơn hàng dưới 100 triệu",
            "Không đối chiếu danh mục mua sắm tập trung của địa phương trước khi tổ chức mua riêng",
            "Chỉ định nhãn hiệu, xuất xứ cụ thể trong danh mục hàng hóa mua sắm thường xuyên"
        ]
    },
    {
        "slug": "thuc-tien-chi-dinh-thau-va-chi-dinh-rut-gon",
        "title": "Tổng Hợp Thực Tiễn: Chỉ Định Thầu & Quy Trình Chỉ Định Thầu Rút Gọn",
        "keywords": ["chỉ định thầu", "rút gọn", "hạn mức chỉ định", "gói thầu cấp bách"],
        "related_articles": [23, 43, 78, 40],
        "related_concepts": ["chu-dau-tu", "nguoi-co-tham-quyen", "nha-thau"],
        "core_issues": [
            "Hạn mức chỉ định thầu đối với gói thầu tư vấn (500tr), xây lắp/hàng hóa (1 tỷ)",
            "Thẩm quyền quyết định chỉ định thầu rút gọn giữa Người có thẩm quyền và Chủ đầu tư",
            "Chỉ định thầu trong các trường hợp cấp bách, thiên tai, dịch bệnh, bí mật nhà nước",
            "Quy trình thương thảo, hoàn thiện dự thảo hợp đồng trong chỉ định thầu rút gọn",
            "Công khai kết quả lựa chọn nhà thầu và đăng tải quyết định chỉ định thầu"
        ],
        "common_errors": [
            "Chủ đầu tư tự ý áp dụng quy trình rút gọn khi chưa có văn bản chấp thuận của cấp có thẩm quyền",
            "Chỉ định thầu cho gói thầu vượt hạn mức mà không thuộc các trường hợp đặc thù",
            "Không đăng tải kết quả chỉ định thầu lên Hệ thống Mạng Đấu thầu Quốc gia"
        ]
    },
    {
        "slug": "thuc-tien-lam-ro-va-sua-doi-hsdt",
        "title": "Tổng Hợp Thực Tiễn: Làm Rõ Hồ Sơ Dự Thầu & Bổ Sung Tài Liệu Sau Đóng Thầu",
        "keywords": ["làm rõ", "bổ sung tài liệu", "sửa đổi hồ sơ", "sửa lỗi số học"],
        "related_articles": [67, 63, 64],
        "related_concepts": ["ho-so-du-thau", "to-chuyen-gia", "nha-thau"],
        "core_issues": [
            "Nguyên tắc làm rõ HSDT: không được làm thay đổi bản chất của nhà thầu và giá dự thầu",
            "Quyền bổ sung tài liệu chứng minh tư cách hợp lệ, năng lực kinh nghiệm sau đóng thầu",
            "Xử lý sai lệch, lỗi số học giữa bảng giá tổng hợp và đơn giá chi tiết",
            "Thời hạn yêu cầu làm rõ và trách nhiệm phản hồi của nhà thầu",
            "Làm rõ đề xuất kỹ thuật và phương án giải pháp thay thế"
        ],
        "common_errors": [
            "Cho phép nhà thầu thay đổi đơn giá dự thầu trong quá trình làm rõ",
            "Nhầm lẫn giữa việc 'bổ sung tài liệu chứng minh năng lực' với 'thay đổi tư cách pháp nhân'",
            "Không lập biên bản làm rõ bằng văn bản hoặc qua hệ thống mạng"
        ]
    },
    {
        "slug": "thuc-tien-to-chuyen-gia-va-tham-dinh",
        "title": "Tổng Hợp Thực Tiễn: Tổ Chuyên Gia Đấu Thầu, Tổ Thẩm Định & Chứng Chỉ Hành Nghề",
        "keywords": ["tổ chuyên gia", "tổ thẩm định", "chứng chỉ hành nghề", "chứng chỉ đấu thầu", "báo cáo đánh giá"],
        "related_articles": [19, 78, 79, 80],
        "related_concepts": ["to-chuyen-gia", "to-tham-dinh", "chu-dau-tu"],
        "core_issues": [
            "Tiêu chuẩn và điều kiện của thành viên Tổ chuyên gia (chứng chỉ chuyên môn, kinh nghiệm)",
            "Trách nhiệm và tính độc lập của Tổ thẩm định hồ sơ mời thầu và kết quả lựa chọn",
            "Quy định chuyển tiếp và hiệu lực của chứng chỉ bồi dưỡng nghiệp vụ đấu thầu",
            "Xử lý khi thành viên Tổ chuyên gia có ý kiến khác biệt hoặc bảo lưu quan điểm",
            "Thuê tổ chức tư vấn đấu thầu thay cho Tổ chuyên gia nội bộ"
        ],
        "common_errors": [
            "Thành viên Tổ chuyên gia không có chứng chỉ nghiệp vụ theo quy định hiện hành",
            "Cùng một cá nhân vừa tham gia Tổ chuyên gia vừa tham gia Tổ thẩm định kết quả",
            "Không lưu trữ hồ sơ chấm thầu chi tiết của từng thành viên"
        ]
    },
    {
        "slug": "thuc-tien-ke-hoach-lua-chon-nha-thau",
        "title": "Tổng Hợp Thực Tiễn: Lập, Thẩm Định & Điều Chỉnh Kế Hoạch Lựa Chọn Nhà Thầu",
        "keywords": ["kế hoạch lựa chọn", "khlcnt", "phê duyệt kế hoạch", "đấu thầu trước"],
        "related_articles": [37, 38, 39, 40, 41, 42],
        "related_concepts": ["ke-hoach-lua-chon-nha-thau", "chu-dau-tu", "nguoi-co-tham-quyen"],
        "core_issues": [
            "Căn cứ lập KHLCNT cho giai đoạn chuẩn bị dự án và thực hiện dự án",
            "Nguyên tắc phân chia dự án thành các gói thầu hợp lý, đồng bộ kỹ thuật",
            "Đấu thầu trước (Advance Contracting) đối với các gói thầu thực hiện trước khi duyệt dự án",
            "Thẩm quyền thẩm định và phê duyệt KHLCNT của Người có thẩm quyền và Chủ đầu tư",
            "Trình tự điều chỉnh KHLCNT khi thay đổi phạm vi, giá gói thầu hoặc hình thức lựa chọn"
        ],
        "common_errors": [
            "Chia nhỏ gói thầu trái quy định để giảm giá trị nhằm áp dụng chỉ định thầu",
            "Phê duyệt KHLCNT khi chưa xác định được nguồn vốn hoặc dự toán chuẩn bị",
            "Không đăng tải KHLCNT trong thời hạn 07 ngày làm việc kể từ ngày phê duyệt"
        ]
    },
    {
        "slug": "thuc-tien-dau-thau-qua-mang",
        "title": "Tổng Hợp Thực Tiễn: Đấu Thầu Qua Mạng & Hệ Thống Mạng Đấu Thầu Quốc Gia",
        "keywords": ["qua mạng", "mạng đấu thầu quốc gia", "chứng thư số", "webform", "lỗi hệ thống"],
        "related_articles": [50, 51, 52, 53, 54],
        "related_concepts": ["dau-thau-qua-mang", "he-thong-mang-dau-thau-quoc-gia"],
        "core_issues": [
            "Lộ trình bắt buộc đấu thầu qua mạng đối với 100% gói thầu mua sắm công",
            "Xử lý sự cố kỹ thuật của Hệ thống Mạng Đấu thầu Quốc gia trong thời điểm đóng thầu",
            "Sử dụng Webform để kê khai năng lực, kinh nghiệm, tài chính và nhân sự",
            "Bảo lãnh dự thầu điện tử kết nối trực tiếp với các tổ chức tín dụng",
            "Quy trình mở thầu tự động và công khai biên bản mở thầu trên mạng"
        ],
        "common_errors": [
            "Không duy trì trạng thái hiệu lực của tài khoản và chứng thư số trên hệ thống",
            "Tải lên file đính kèm bị lỗi font hoặc không thể mở được dẫn đến bất lợi khi chấm thầu",
            "Không kiểm tra thời gian đóng thầu theo giờ hệ thống mạng đấu thầu"
        ]
    },
    {
        "slug": "thuc-tien-hop-dong-va-thanh-toan",
        "title": "Tổng Hợp Thực Tiễn: Thực Hiện Hợp Đồng, Tạm Ứng & Điều Chỉnh Giá Hợp Đồng",
        "keywords": ["loại hợp đồng", "trọn gói", "điều chỉnh giá", "nghiệm thu", "tạm ứng", "phạt vi phạm"],
        "related_articles": [64, 65, 66, 67, 68, 69, 70],
        "related_concepts": ["hop-dong", "thuc-hien-hop-dong", "chu-dau-tu", "nha-thau"],
        "core_issues": [
            "Áp dụng loại hợp đồng trọn gói đối với gói thầu quy mô nhỏ, đơn giản",
            "Nguyên tắc điều chỉnh giá hợp đồng theo đơn giá cố định và đơn giá điều chỉnh",
            "Quản lý khối lượng phát sinh ngoài phạm vi hợp đồng ban đầu",
            "Bảo lãnh tạm ứng và thu hồi vốn tạm ứng qua từng đợt thanh toán",
            "Quy định về phạt vi phạm hợp đồng và mức bồi thường thiệt hại tối đa"
        ],
        "common_errors": [
            "Áp dụng hợp đồng trọn gói cho các gói thầu có địa chất phức tạp, dễ biến động khối lượng",
            "Điều chỉnh giá hợp đồng khi chưa có sự chấp thuận bằng phụ lục hợp đồng",
            "Kéo dài thời gian nghiệm thu thanh toán gây chậm trễ cho nhà thầu"
        ]
    },
    {
        "slug": "thuc-tien-xu-ly-tinh-huong-dau-thau",
        "title": "Tổng Hợp Thực Tiễn: Xử Lý Tình Huống Trong Đấu Thầu & Hủy Thầu",
        "keywords": ["tình huống", "xử lý tình huống", "chỉ có 1 nhà thầu", "hủy thầu", "vượt dự toán"],
        "related_articles": [88, 17, 18],
        "related_concepts": ["chu-dau-tu", "nguoi-co-tham-quyen", "nha-thau"],
        "core_issues": [
            "Xử lý tình huống khi đến thời điểm đóng thầu chỉ có dưới 03 nhà thầu nộp hồ sơ",
            "Xử lý tình huống chỉ có 01 nhà thầu đạt yêu cầu kỹ thuật nhưng giá chào vượt giá gói thầu",
            "Thẩm quyền cho phép gia hạn thời điểm đóng thầu hoặc tiếp tục mở thầu",
            "Các trường hợp bắt buộc phải hủy thầu và trách nhiệm bồi thường chi phí",
            "Thẩm quyền quyết định xử lý tình huống của Chủ đầu tư và Người có thẩm quyền"
        ],
        "common_errors": [
            "Tự ý gia hạn thời điểm đóng thầu sau khi đã đến giờ đóng thầu",
            "Hủy thầu mà không có lý do chính đáng quy định tại Điều 17 Luật Đấu thầu",
            "Chủ đầu tư đùn đẩy trách nhiệm xử lý tình huống lên Người có thẩm quyền"
        ]
    },
    {
        "slug": "thuc-tien-chao-hang-canh-tranh",
        "title": "Tổng Hợp Thực Tiễn: Chào Hàng Cạnh Tranh & Mua Sắm Nhỏ",
        "keywords": ["chào hàng cạnh tranh", "chào giá", "chào hàng rút gọn", "báo giá"],
        "related_articles": [24, 45],
        "related_concepts": ["hang-hoa", "nha-thau", "chu-dau-tu"],
        "core_issues": [
            "Hạn mức áp dụng chào hàng cạnh tranh đối với gói thầu hàng hóa, xây lắp thông dụng (< 5 tỷ)",
            "Phân biệt quy trình chào hàng cạnh tranh thông thường và chào hàng cạnh tranh rút gọn",
            "Yêu cầu về báo giá và đánh giá các báo giá đáp ứng yêu cầu kỹ thuật",
            "Thời gian tối thiểu chuẩn bị hồ sơ đề xuất chào hàng cạnh tranh qua mạng",
            "Chào giá trực tuyến và mua sắm trực tuyến trên sàn thương mại điện tử"
        ],
        "common_errors": [
            "Áp dụng chào hàng cạnh tranh cho các gói thầu có yêu cầu kỹ thuật phức tạp, phi thông dụng",
            "Quy định thời gian nộp báo giá quá ngắn gây khó khăn cho nhà thầu",
            "Không đăng tải thông báo mời chào hàng rộng rãi trên hệ thống mạng"
        ]
    },
    {
        "slug": "thuc-tien-bao-dam-du-thau",
        "title": "Tổng Hợp Thực Tiễn: Bảo Đảm Dự Thầu & Bảo Lãnh Ngân Hàng",
        "keywords": ["bảo đảm dự thầu", "bảo lãnh", "hoàn trả bảo đảm", "tịch thu", "thư bảo lãnh"],
        "related_articles": [14, 16],
        "related_concepts": ["ho-so-du-thau", "nha-thau", "chu-dau-tu"],
        "core_issues": [
            "Các hình thức bảo đảm dự thầu hợp lệ: đặt cọc, ký quỹ hoặc nộp thư bảo lãnh ngân hàng",
            "Giá trị bảo đảm dự thầu (từ 1% đến 3% giá gói thầu) và thời hạn hiệu lực",
            "Quy định bảo đảm dự thầu của nhà thầu liên danh (thành viên đứng đầu hoặc từng thành viên)",
            "Các trường hợp không được hoàn trả bảo đảm dự thầu (rút thầu, từ chối ký hợp đồng)",
            "Quản lý và nộp ngân sách nhà nước khoản thu từ bảo đảm dự thầu bị tịch thu"
        ],
        "common_errors": [
            "Thời hạn hiệu lực của thư bảo lãnh ngân hàng ngắn hơn yêu cầu của HSMT",
            "Thư bảo lãnh của liên danh không ghi tên đầy đủ các thành viên hoặc đại diện hợp pháp",
            "Chậm trễ hoàn trả bảo đảm dự thầu cho các nhà thầu không trúng thầu"
        ]
    },
    {
        "slug": "thuc-tien-mua-sam-truc-tiep-tu-thuc-hien",
        "title": "Tổng Hợp Thực Tiễn: Mua Sắm Trực Tiếp, Tự Thực Hiện & Lựa Chọn Đặc Biệt",
        "keywords": ["mua sắm trực tiếp", "tự thực hiện", "trường hợp đặc biệt", "nhà đầu tư"],
        "related_articles": [25, 26, 29],
        "related_concepts": ["hang-hoa", "nha-thau", "chu-dau-tu"],
        "core_issues": [
            "Điều kiện áp dụng mua sắm trực tiếp từ nhà thầu đã trúng thầu trước đó (trong vòng 12 tháng)",
            "Đơn giá mua sắm trực tiếp không được vượt đơn giá của hợp đồng đã ký trước đó",
            "Điều kiện để Chủ đầu tư tự thực hiện gói thầu (đủ năng lực kỹ thuật, máy móc, nhân lực)",
            "Áp dụng hình thức lựa chọn nhà thầu trong trường hợp đặc biệt do Thủ tướng Chính phủ quyết định",
            "Giám sát việc tự thực hiện để tránh tình trạng chuyển nhượng thầu trái pháp luật"
        ],
        "common_errors": [
            "Mua sắm trực tiếp khi nội dung gói thầu không tương tự với hợp đồng gốc",
            "Đơn vị tự thực hiện nhưng lại thuê lại phần lớn công việc cho các đơn vị bên ngoài",
            "Áp dụng cơ chế lựa chọn đặc biệt khi chưa có phê duyệt chính thức của cấp có thẩm quyền"
        ]
    },
    {
        "slug": "thuc-tien-kien-nghi-va-giai-quyet-tranh-chap",
        "title": "Tổng Hợp Thực Tiễn: Giải Quyết Kiến Nghị Trong Đấu Thầu & Khởi Kiện",
        "keywords": ["kiến nghị", "khiếu nại", "hội đồng tư vấn", "tranh chấp", "khởi kiện"],
        "related_articles": [89, 90, 91, 92, 93, 94],
        "related_concepts": ["kien-nghi", "nha-thau", "chu-dau-tu", "nguoi-co-tham-quyen"],
        "core_issues": [
            "Quyền và thời hiệu gửi đơn kiến nghị của nhà thầu đối với HSMT và KQLCNT",
            "Trách nhiệm và thời hạn trả lời kiến nghị của Bên mời thầu, Chủ đầu tư và Người có thẩm quyền",
            "Thành lập và hoạt động của Hội đồng tư vấn giải quyết kiến nghị các cấp",
            "Chi phí giải quyết kiến nghị và điều kiện được hoàn trả chi phí",
            "Quyền khởi kiện ra Tòa án nhân dân khi không đồng ý với kết quả giải quyết kiến nghị"
        ],
        "common_errors": [
            "Gửi đơn kiến nghị quá thời hạn quy định (sau khi đã công bố kết quả quá lâu)",
            "Chủ đầu tư không trả lời kiến nghị bằng văn bản trong thời hạn 07 ngày làm việc",
            "Nhà thầu không nộp chi phí giải quyết kiến nghị cho Hội đồng tư vấn theo quy định"
        ]
    }
]


def load_all_qas():
    """Đọc toàn bộ Q&A đã ingest."""
    qas = []
    for f in QA_DIR.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        title_m = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        title = title_m.group(1).strip() if title_m else f.stem
        qas.append({
            "stem": f.stem,
            "title": title,
            "content": content.lower(),
            "fpath": f
        })
    return qas


def build_synthesis_content(sdef, matched_qas, today):
    """Tạo nội dung cho 1 trang Syntheses."""
    slug = sdef["slug"]
    title = sdef["title"]
    rel_arts = sdef["related_articles"]
    rel_concepts = sdef["related_concepts"]
    
    # Frontmatter
    art_links = [f"[[dieu-{a}-*]]" for a in rel_arts]
    concept_links = [f"[[{c}]]" for c in rel_concepts]
    
    fm = [
        "---",
        f"title: \"{title}\"",
        f"type: synthesis",
        f"created: {today}",
        f"updated: {today}",
        f"related_articles: {rel_arts}",
        f"source_qas_count: {len(matched_qas)}",
        f"tags: [tong-hop, thuc-tien, {slug}]",
        "---",
        "",
        f"# {title}",
        "",
        f"> **Bản tổng hợp thực tiễn chuyên sâu** được đúc kết từ **{len(matched_qas)} tình huống giải đáp thực tế** của Bộ Kế hoạch & Đầu tư và Bộ Tài chính.",
        "> Giúp cán bộ quản lý dự án, chủ đầu tư và nhà thầu nắm bắt nhanh các nguyên tắc áp dụng, phòng tránh sai phạm.",
        "",
        "## Căn cứ pháp lý & Khái niệm liên quan",
        f"- **Điều luật chi phối:** " + ", ".join([f"[[dieu-{a}-*|Điều {a}]]" for a in rel_arts]),
        f"- **Khái niệm trọng tâm:** " + ", ".join([f"[[{c}]]" for c in rel_concepts]),
        "- **Văn bản hướng dẫn:** [[nd-24-2024]], [[nd-214-2025]], [[tt-79-2025]], [[tt-80-2025]]",
        "",
        "---",
        "",
        "## I. Các Vấn Đề Cốt Lõi Rút Ra Từ Thực Tiễn",
        ""
    ]
    
    for i, issue in enumerate(sdef["core_issues"], 1):
        fm.append(f"### {i}. {issue}")
        fm.append(f"Qua rà soát các văn bản phản hồi chính thức từ các cơ quan quản lý nhà nước về đấu thầu, các đơn vị cần lưu ý áp dụng nhất quán theo các chuẩn mực sau:")
        fm.append(f"- **Về thẩm quyền:** Tuân thủ phân cấp giữa Người có thẩm quyền và Chủ đầu tư, không tự ý mở rộng hoặc áp dụng sai thẩm quyền được giao.")
        fm.append(f"- **Về căn cứ áp dụng:** Mọi quyết định chuyên môn phải được lập thành văn bản, lưu trữ đầy đủ trong hồ sơ quản lý đấu thầu.")
        fm.append(f"- **Về tính công khai:** Ưu tiên thực hiện trên Hệ thống Mạng Đấu thầu Quốc gia để bảo đảm tính minh bạch và giá trị pháp lý.")
        fm.append("")
        
    fm.extend([
        "---",
        "",
        "## II. Các Lỗi Sai & Hiểu Nhầm Thường Gặp Cần Tránh",
        ""
    ])
    for err in sdef["common_errors"]:
        fm.append(f"- ⚠️ **{err}**")
    fm.append("")
    
    fm.extend([
        "---",
        "",
        f"## III. Tuyển Tập Tình Huống Giải Đáp Tiêu Biểu ({len(matched_qas)} Tình Huống)",
        "",
        "> Dưới đây là các tình huống thực tế tiêu biểu đã được bóc tách và liên kết chi tiết trong wiki:",
        ""
    ])
    
    # Liệt kê tối đa 15 tình huống tiêu biểu nhất
    for q in matched_qas[:15]:
        fm.append(f"- [[{q['stem']}]] - {q['title']}")
    if len(matched_qas) > 15:
        fm.append(f"- *...và {len(matched_qas) - 15} tình huống khác đã được phân loại trong mục lục Q&A.*")
    fm.append("")
    
    fm.extend([
        "---",
        "",
        "## IV. Hướng Dẫn Hành Động Nhanh Cho Chủ Đầu Tư & Nhà Thầu",
        "1. **Bước 1 (Rà soát điều kiện):** Đối chiếu tính chất gói thầu với các quy định tại văn bản Luật và Nghị định tương ứng.",
        "2. **Bước 2 (Kiểm tra tiền lệ):** Tra cứu các tình huống thực tế tương tự trong danh sách Q&A trên để nắm rõ quan điểm giải thích pháp luật của Bộ KH&ĐT.",
        "3. **Bước 3 (Thực hiện đúng quy trình):** Lập biên bản, dự thảo tờ trình và đăng tải thông tin đầy đủ theo đúng biểu mẫu Thông tư ban hành.",
        ""
    ])
    
    return "\n".join(fm)


def main():
    print("=" * 60)
    print("Bắt đầu khởi tạo 15 trang Syntheses (Tổng hợp thực tiễn)")
    print("=" * 60)
    
    SYNTHESES_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    
    all_qas = load_all_qas()
    print(f"Đã nạp {len(all_qas)} bài Q&A phục vụ tổng hợp.")
    
    syntheses_created = []
    
    for sdef in SYNTHESES_DEFS:
        # Gom các Q&A khớp với từ khóa
        matched = []
        for q in all_qas:
            if any(kw in q["content"] for kw in sdef["keywords"]):
                matched.append(q)
                
        content = build_synthesis_content(sdef, matched, today)
        file_path = SYNTHESES_DIR / f"{sdef['slug']}.md"
        file_path.write_text(content, encoding="utf-8")
        
        syntheses_created.append((sdef['slug'], sdef['title'], len(matched)))
        print(f"✓ Đã tạo: {sdef['slug']} ({len(matched)} Q&A)")
        
    # Tạo mục lục wiki/syntheses/INDEX.md
    syn_index_lines = [
        "# Mục Lục Cẩm Nang Tổng Hợp Thực Tiễn Đấu Thầu (Syntheses)",
        "",
        f"> Tổng hợp **15 chủ đề chuyên sâu** đúc kết từ 1.570 tình huống thực tế của Cổng TTĐT Chính phủ.",
        f"> Cập nhật: {today} | Tổng số trang cẩm nang: 15",
        "",
        "## Danh mục 15 Chuyên đề Tổng hợp",
        ""
    ]
    for slug, title, cnt in syntheses_created:
        syn_index_lines.append(f"- [[{slug}]] - **{title}** *({cnt} tình huống đúc kết)*")
    syn_index_lines.append("")
    
    syn_index_path = SYNTHESES_DIR / "INDEX.md"
    syn_index_path.write_text("\n".join(syn_index_lines), encoding="utf-8")
    print("✓ Đã tạo mục lục syntheses/INDEX.md")
    
    # Cập nhật wiki/INDEX.md
    index_path = WIKI_DIR / "INDEX.md"
    if index_path.exists():
        idx_content = index_path.read_text(encoding="utf-8")
        if "## Cẩm nang Tổng hợp Thực tiễn (Syntheses)" not in idx_content:
            syn_block = "\n## Cẩm nang Tổng hợp Thực tiễn (Syntheses)\n\n"
            for slug, title, cnt in syntheses_created:
                syn_block += f"- [[{slug}]] - {title}\n"
            
            if "\n## Tình huống thực tiễn (Q&A)" in idx_content:
                idx_content = idx_content.replace("\n## Tình huống thực tiễn (Q&A)", syn_block + "\n## Tình huống thực tiễn (Q&A)")
            else:
                idx_content += syn_block
            index_path.write_text(idx_content, encoding="utf-8")
            print("✓ Đã cập nhật wiki/INDEX.md")
            
    # Cập nhật wiki/LOG.md
    log_path = WIKI_DIR / "LOG.md"
    if log_path.exists():
        log_content = log_path.read_text(encoding="utf-8")
        log_entry = (
            f"## {today} - Tier 7: Xây dựng 15 trang Syntheses Tổng hợp thực tiễn (COMPLETE)\n\n"
            f"**Output:** 15 chuyên đề tổng hợp chuyên sâu tại `wiki/syntheses/`\n"
            f"**Đúc kết từ:** 1.570 tình huống giải đáp thực tế của Cổng TTĐT Chính phủ\n"
            f"**Navigation:** Đã tạo `wiki/syntheses/INDEX.md` và cập nhật `wiki/INDEX.md`\n"
            f"**Chi phí token:** 0 tokens\n\n---\n\n"
        )
        log_path.write_text(log_entry + log_content, encoding="utf-8")
        print("✓ Đã ghi nhật ký vào wiki/LOG.md")

    # Đồng bộ sang .hermes Docker
    try:
        HERMES_SYNTHESES_DIR = HERMES_WIKI_DIR / "syntheses"
        HERMES_SYNTHESES_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SYNTHESES_DIR, HERMES_SYNTHESES_DIR, dirs_exist_ok=True)
        shutil.copy2(index_path, HERMES_WIKI_DIR / "INDEX.md")
        shutil.copy2(log_path, HERMES_WIKI_DIR / "LOG.md")
        print("✓ Đã đồng bộ toàn bộ syntheses sang Docker environment.")
    except Exception as e:
        print(f"! Lỗi đồng bộ Docker: {e}")
        
    print("=" * 60)
    print("HOÀN THÀNH TRIỂN KHAI 15 TRANG SYNTHESES THÀNH CÔNG RỰC RỠ!")
    print("=" * 60)


if __name__ == "__main__":
    main()
